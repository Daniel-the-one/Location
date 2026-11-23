"""Amorce idempotente du compte développeur/admin.

Appelée au démarrage du Web Service Render. Les identifiants viennent de variables
d'environnement générées par Render : ils ne sont jamais écrits dans le dépôt, les
logs ou cette commande. Un mot de passe existant n'est jamais réinitialisé.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import User as AccountUser


class Command(BaseCommand):
    help = "Crée le compte admin à partir de ESSIVIVI_ADMIN_EMAIL / ESSIVIVI_ADMIN_PASSWORD."

    def handle(self, *args, **options):
        email = os.environ.get("ESSIVIVI_ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("ESSIVIVI_ADMIN_PASSWORD", "")
        if not email or not password:
            self.stdout.write(
                "ensure_admin : variables absentes, aucun compte créé "
                "(ATTENDU en local, à renseigner sur Render)."
            )
            return

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            User.objects.create_superuser(email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"ensure_admin : compte admin créé ({email})."))
            return

        changed = []
        if user.role != AccountUser.Role.ADMIN:
            user.role = AccountUser.Role.ADMIN
            changed.append("role")
        if not user.is_staff:
            user.is_staff = True
            changed.append("is_staff")
        if not user.is_superuser:
            user.is_superuser = True
            changed.append("is_superuser")
        if user.status != AccountUser.Status.ACTIVE:
            user.status = AccountUser.Status.ACTIVE
            changed.append("status")
        if changed:
            user.save(update_fields=changed)
            self.stdout.write(
                self.style.SUCCESS(f"ensure_admin : compte existant promu admin ({', '.join(changed)}).")
            )
        else:
            self.stdout.write("ensure_admin : compte admin déjà présent, mot de passe inchangé.")
