"""Recette de bout en bout sur une instance déployée, sans secret affiché.

Usage : python manage.py smoke_prod

Vérifie la chaîne complète : déclaration publique -> rien de publié -> refus de
publication sans identité -> vérification de l'identité -> publication -> retrait
sur suspension, plus l'accès au document privé et son absence sous /media/.
Le dossier de test est supprimé en fin de recette, y compris les fichiers.
Les identifiants admin viennent de l'environnement et ne sont jamais imprimés.
"""
import io
import os
import uuid

from PIL import Image
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from rest_framework.test import APIClient

from apps.accounts.models import IdentityVerification, User
from apps.exchanges.models import Notification
from apps.properties.models import Property

def tiny_png():
    """Image de test valide, générée en mémoire (aucun fichier sur le disque)."""
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), (210, 185, 140)).save(buffer, format="PNG")
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Recette E2E de la modération sur l'instance courante (données nettoyées)."

    def verify(self, label, ok, response=None):
        if not ok:
            detail = ""
            if response is not None:
                detail = " (HTTP {0}, {1})".format(
                    response.status_code, str(getattr(response, "data", ""))[:200]
                )
            raise CommandError("ÉCHEC : {0}{1}".format(label, detail))
        self.stdout.write("  OK   {0}".format(label))

    def handle(self, *args, **options):
        email = os.environ.get("ESSIVIVI_ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("ESSIVIVI_ADMIN_PASSWORD", "")
        if not email or not password:
            raise CommandError(
                "ESSIVIVI_ADMIN_EMAIL et ESSIVIVI_ADMIN_PASSWORD doivent être définis."
            )
        admin = User.objects.filter(email__iexact=email, role=User.Role.ADMIN).first()
        if not admin or not admin.check_password(password):
            raise CommandError("Compte admin introuvable ou mot de passe incorrect.")

        host = next((h for h in settings.ALLOWED_HOSTS if h and "*" not in h), "testserver")
        visitor = APIClient(HTTP_HOST=host, secure=True)
        admin_client = APIClient(HTTP_HOST=host, secure=True)

        self.stdout.write("Recette de modération — hôte de test : {0}".format(host))
        response = admin_client.post(
            "/api/auth/login/", {"email": email, "password": password}, format="json"
        )
        self.verify("connexion admin (JWT)", response.status_code == 200, response)
        admin_client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])

        response = admin_client.get("/api/admin/overview/")
        self.verify("tableau de bord admin accessible", response.status_code == 200, response)
        response = visitor.get("/api/admin/overview/")
        self.verify("tableau de bord fermé au visiteur", response.status_code in (401, 403), response)

        marker = uuid.uuid4().hex[:10]
        title = "RECETTE-AUTO-{0}".format(marker)
        owner_email = "recette-{0}@example.invalid".format(marker)
        payload = {
            "first_name": "Recette",
            "last_name": "Automatique",
            "email": owner_email,
            "phone": "+22890000000",
            "password": "Smoke-{0}-A1!".format(marker),
            "property_type": "studio",
            "title": title,
            "address": "{0} rue de la Recette".format(marker),
            "neighborhood": "Recette",
            "city": "Lome",
            "rent": 125000,
            "charges": 0,
            "deposit": 0,
            "rooms_count": 1,
            "description": "Dossier de recette automatique, supprimé en fin de test.",
            "consent": True,
            "website": "",
            "entrance_photo": SimpleUploadedFile(
                "entree.png", tiny_png(), content_type="image/png"
            ),
            "identity_document": SimpleUploadedFile(
                "piece.png", tiny_png(), content_type="image/png"
            ),
        }

        prop = None
        identity = None
        owner = None
        try:
            response = visitor.post("/api/declarations/", payload, format="multipart")
            self.verify("déclaration publique enregistrée", response.status_code == 201, response)
            self.verify(
                "accusé de réception avec dossier",
                str(response.data.get("dossier", "")).startswith("ESS-"),
                response,
            )

            prop = Property.objects.get(title=title)
            identity = IdentityVerification.objects.get(user=prop.owner)
            owner = prop.owner
            self.verify(
                "bien en attente et marqué web",
                prop.status == Property.Status.PENDING
                and prop.source == Property.Source.WEB,
            )
            self.verify("identité en attente", identity.status == IdentityVerification.Status.PENDING)

            response = visitor.get("/api/properties/")
            self.verify(
                "bien invisible avant modération",
                all(item["id"] != prop.id for item in response.data.get("results", [])),
                response,
            )

            response = admin_client.post(
                "/api/admin/properties/{0}/approve/".format(prop.id), {}, format="json"
            )
            self.verify("publication refusée sans identité vérifiée", response.status_code == 409, response)

            response = admin_client.post(
                "/api/admin/identities/{0}/approve/".format(identity.id), {}, format="json"
            )
            self.verify("identité vérifiée par l'admin", response.status_code == 200, response)

            response = admin_client.post(
                "/api/admin/properties/{0}/approve/".format(prop.id), {}, format="json"
            )
            self.verify("bien publié après vérification", response.status_code == 200, response)

            response = visitor.get("/api/properties/")
            self.verify(
                "bien visible sur le site client",
                any(item["id"] == prop.id for item in response.data.get("results", [])),
                response,
            )

            response = admin_client.get(
                "/api/admin/identities/{0}/document/".format(identity.id)
            )
            try:
                self.verify(
                    "pièce d'identité lisible par l'admin",
                    response.status_code == 200
                    and str(response.get("Content-Type", "")).startswith("image/"),
                    response,
                )
                self.verify(
                    "document avec en-têtes de sécurité",
                    response.get("X-Content-Type-Options") == "nosniff"
                    and "sandbox" in response.get("Content-Security-Policy", ""),
                )
                # FileResponse garde un descripteur ouvert tant que le flux n'est pas consommé.
                if getattr(response, "streaming", False):
                    b"".join(response.streaming_content)
            finally:
                response.close()
            response = visitor.get("/media/{0}".format(identity.document.name))
            self.verify("document indisponible sous /media/", response.status_code in (403, 404))

            response = admin_client.post(
                "/api/admin/properties/{0}/suspend/".format(prop.id),
                {"reason": "Recette automatique"},
                format="json",
            )
            self.verify("bien suspendu par l'admin", response.status_code == 200, response)
            response = visitor.get("/api/properties/")
            self.verify(
                "bien retiré du site après suspension",
                all(item["id"] != prop.id for item in response.data.get("results", [])),
                response,
            )
            self.stdout.write(self.style.SUCCESS("Recette réussie : chaîne complète validée."))
        finally:
            # Aucune donnée ni aucun fichier de test ne reste sur l'instance.
            if prop is not None:
                Notification.objects.filter(content__icontains=title).delete()
                try:
                    prop.entrance_photo.delete(save=False)
                except OSError:
                    self.stdout.write("Attention : photo de test non supprimée du stockage.")
                prop.delete()
            if identity is not None:
                try:
                    identity.document.delete(save=False)
                except OSError:
                    self.stdout.write("Attention : document de test non supprimé du stockage.")
                identity.delete()
            if owner is not None:
                owner.delete()
            self.stdout.write("Nettoyage du dossier de test effectué.")
