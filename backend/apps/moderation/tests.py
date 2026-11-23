import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from apps.accounts.models import IdentityVerification, User
from apps.properties.models import Property

TMP_MEDIA = tempfile.mkdtemp()
TMP_PRIVATE = tempfile.mkdtemp()
PASSWORD = "Lome-2026-secure"


def jpeg():
    buffer = io.BytesIO()
    Image.new("RGB", (600, 400), (120, 160, 200)).save(buffer, format="JPEG")
    return SimpleUploadedFile("porte.jpg", buffer.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=TMP_MEDIA, PRIVATE_MEDIA_ROOT=TMP_PRIVATE)
class ModerationTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)
        shutil.rmtree(TMP_PRIVATE, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="Admin-2026-secure"
        )
        self.owner = User.objects.create_user(
            email="owner@example.com", password=PASSWORD, role=User.Role.OWNER
        )
        self.identity = IdentityVerification.objects.create(
            user=self.owner,
            document=SimpleUploadedFile("cni.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
        )
        self.prop = Property.objects.create(
            owner=self.owner,
            source=Property.Source.WEB,
            status=Property.Status.PENDING,
            property_type="apartment",
            title="Appartement à Bè",
            address="Rue 12",
            neighborhood="Bè",
            city="Lomé",
            rent=75000,
            entrance_photo=jpeg(),
        )

    def test_admin_only(self):
        self.assertEqual(self.client.get("/api/admin/overview/").status_code, 401)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get("/api/admin/overview/").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/properties/").status_code, 403)

    def test_overview_counts_pending(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get("/api/admin/overview/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["properties"]["pending"], 1)
        self.assertEqual(res.data["identities"]["pending"], 1)
        self.assertEqual(res.data["web_declarations"], 1)
        self.assertEqual(res.data["recent"][0]["dossier"], f"ESS-{self.prop.pk:06d}")

    def test_web_declaration_cannot_be_published_before_identity(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(f"/api/admin/properties/{self.prop.pk}/approve/")
        self.assertEqual(res.status_code, 409)

        res = self.client.post(f"/api/admin/identities/{self.identity.pk}/approve/")
        self.assertEqual(res.status_code, 200, res.data)
        self.identity.refresh_from_db()
        self.assertEqual(self.identity.status, IdentityVerification.Status.APPROVED)

        res = self.client.post(f"/api/admin/properties/{self.prop.pk}/approve/")
        self.assertEqual(res.status_code, 200, res.data)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, Property.Status.PUBLISHED)
        # La vitrine ne lit que les annonces publiées.
        public = self.client.get("/api/properties/").data["results"]
        self.assertEqual(len(public), 1)
        self.assertEqual(public[0]["id"], self.prop.id)

    def test_reject_requires_reason_and_updates_status(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.post(f"/api/admin/properties/{self.prop.pk}/reject/", {}).status_code, 400
        )
        res = self.client.post(
            f"/api/admin/properties/{self.prop.pk}/reject/", {"reason": "Photo illisible"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, Property.Status.REJECTED)
        self.assertEqual(self.prop.rejection_reason, "Photo illisible")
        self.assertEqual(self.client.get("/api/properties/").data["results"], [])

    def test_suspend_and_unsuspend(self):
        self.client.force_authenticate(self.admin)
        self.client.post(f"/api/admin/identities/{self.identity.pk}/approve/")
        self.client.post(f"/api/admin/properties/{self.prop.pk}/approve/")

        res = self.client.post(
            f"/api/admin/properties/{self.prop.pk}/suspend/", {"reason": "Signalement"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.prop.refresh_from_db()
        self.assertTrue(self.prop.suspended_by_admin)
        self.assertEqual(self.client.get("/api/properties/").data["results"], [])

        res = self.client.post(f"/api/admin/properties/{self.prop.pk}/unsuspend/")
        self.assertEqual(res.status_code, 200, res.data)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, Property.Status.PUBLISHED)
        self.assertFalse(self.prop.suspended_by_admin)

    def test_identity_document_is_private_and_isolated(self):
        self.assertEqual(
            self.client.get(f"/api/admin/identities/{self.identity.pk}/document/").status_code, 401
        )
        self.client.force_authenticate(self.admin)
        res = self.client.get(f"/api/admin/identities/{self.identity.pk}/document/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertEqual(res["X-Content-Type-Options"], "nosniff")
        self.assertIn("sandbox", res["Content-Security-Policy"])

    def test_filters_by_status_and_source(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get("/api/admin/properties/?status=pending&source=web")
        self.assertEqual(len(res.data["results"]), 1)
        res = self.client.get("/api/admin/properties/?status=published")
        self.assertEqual(len(res.data["results"]), 0)
