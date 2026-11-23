import io
import shutil
import tempfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from apps.accounts.models import IdentityVerification, User
from apps.exchanges.models import Notification

from .models import Property

TMP_MEDIA = tempfile.mkdtemp()
TMP_PRIVATE = tempfile.mkdtemp()
URL = "/api/declarations/"


def image(name="porte.jpg"):
    buffer = io.BytesIO()
    Image.new("RGB", (800, 600), (200, 180, 140)).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def payload(**over):
    data = {
        "first_name": "Aminata",
        "last_name": "Kossi",
        "email": "aminata@example.com",
        "phone": "90123456",
        "password": "Lome-2026-secure",
        "property_type": "apartment",
        "title": "Appartement à Bè",
        "address": "Rue des Écoles",
        "neighborhood": "Bè",
        "city": "Lomé",
        "rent": "85000",
        "description": "Deux pièces, eau et électricité.",
        "entrance_photo": image(),
        "identity_document": SimpleUploadedFile(
            "cni.pdf", b"%PDF-1.4 faux document de test", content_type="application/pdf"
        ),
        "consent": "true",
    }
    data.update(over)
    return data


@override_settings(
    MEDIA_ROOT=TMP_MEDIA,
    PRIVATE_MEDIA_ROOT=TMP_PRIVATE,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "decl"}},
)
class DeclarationTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)
        shutil.rmtree(TMP_PRIVATE, ignore_errors=True)

    def setUp(self):
        cache.clear()

    def test_declaration_creates_owner_identity_and_pending_property(self):
        User.objects.create_superuser(email="admin@example.com", password="Admin-2026-secure")
        res = self.client.post(URL, payload(), format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["status"], "pending")
        self.assertTrue(res.data["dossier"].startswith("ESS-"))

        owner = User.objects.get(email="aminata@example.com")
        self.assertEqual(owner.role, User.Role.OWNER)
        self.assertTrue(owner.check_password("Lome-2026-secure"))
        self.assertEqual(owner.phone, "+22890123456")

        prop = Property.objects.get(owner=owner)
        self.assertEqual(prop.status, Property.Status.PENDING)
        self.assertEqual(prop.source, Property.Source.WEB)
        self.assertEqual(prop.city, "Lomé")
        self.assertTrue(prop.entrance_photo)

        identity = IdentityVerification.objects.get(user=owner)
        self.assertEqual(identity.status, IdentityVerification.Status.PENDING)
        self.assertTrue(identity.document)

        admin = User.objects.get(email="admin@example.com")
        self.assertTrue(
            Notification.objects.filter(user=admin, kind="new_declaration").exists()
        )

    def test_honeypot_is_silently_accepted_without_writing(self):
        res = self.client.post(URL, payload(website="https://spam.example"), format="multipart")
        self.assertEqual(res.status_code, 201)
        self.assertFalse(User.objects.filter(email="aminata@example.com").exists())
        self.assertEqual(Property.objects.count(), 0)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email="aminata@example.com", password="Lome-2026-secure")
        res = self.client.post(URL, payload(), format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data)
        self.assertEqual(Property.objects.count(), 0)

    def test_consent_is_required(self):
        res = self.client.post(URL, payload(consent="false"), format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Property.objects.count(), 0)

    def test_weak_password_rejected(self):
        res = self.client.post(URL, payload(password="123"), format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Property.objects.count(), 0)

    def test_only_five_declarations_per_ip_and_hour(self):
        for index in range(5):
            data = payload(email=f"owner{index}@example.com")
            self.assertEqual(self.client.post(URL, data, format="multipart").status_code, 201)
        res = self.client.post(URL, payload(email="sixieme@example.com"), format="multipart")
        self.assertEqual(res.status_code, 429)
        self.assertEqual(Property.objects.count(), 5)
