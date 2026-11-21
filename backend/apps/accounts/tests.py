import re
import shutil
import tempfile

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import IdentityVerification, User

PASSWORD = "Lome-2026-secure"
TMP_PRIVATE = tempfile.mkdtemp()


def make_user(email="t@example.com", role=User.Role.TENANT, **extra):
    return User.objects.create_user(email=email, password=PASSWORD, role=role, **extra)


class RegisterTests(APITestCase):
    url = reverse("register")

    def payload(self, **over):
        data = {
            "email": "Kofi@Example.com",
            "password": PASSWORD,
            "first_name": "Kofi",
            "last_name": "Mensah",
            "role": "tenant",
        }
        data.update(over)
        return data

    def test_register_tenant_returns_tokens_and_lowercases_email(self):
        res = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", res.data)
        self.assertEqual(res.data["user"]["email"], "kofi@example.com")
        self.assertEqual(res.data["user"]["role"], "tenant")

    def test_register_owner(self):
        res = self.client.post(self.url, self.payload(role="owner"), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertFalse(res.data["user"]["is_identity_verified"])

    def test_cannot_register_as_admin(self):
        res = self.client.post(self.url, self.payload(role="admin"), format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_rejected(self):
        res = self.client.post(self.url, self.payload(password="123"), format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_rejected(self):
        make_user(email="kofi@example.com")
        res = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    url = reverse("login")

    def test_login_returns_tokens_and_user(self):
        make_user()
        res = self.client.post(self.url, {"email": "T@example.com", "password": PASSWORD})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertEqual(res.data["user"]["role"], "tenant")

    def test_wrong_password(self):
        make_user()
        res = self.client.post(self.url, {"email": "t@example.com", "password": "wrong"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_suspended_account_cannot_login(self):
        make_user(status=User.Status.SUSPENDED)
        res = self.client.post(self.url, {"email": "t@example.com", "password": PASSWORD})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_existing_token_stops_working_after_block(self):
        user = make_user()
        res = self.client.post(self.url, {"email": "t@example.com", "password": PASSWORD})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        self.assertEqual(self.client.get(reverse("me")).status_code, 200)
        user.status = User.Status.BLOCKED
        user.save()
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)


class MeTests(APITestCase):
    def test_requires_auth(self):
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)

    def test_update_profile_but_not_role(self):
        user = make_user()
        self.client.force_authenticate(user)
        res = self.client.patch(
            reverse("me"), {"phone": "+22890000000", "role": "admin"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.phone, "+22890000000")
        self.assertEqual(user.role, User.Role.TENANT)


class PasswordResetTests(APITestCase):
    def test_full_reset_flow(self):
        make_user()
        res = self.client.post(reverse("password-reset"), {"email": "t@example.com"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        uid, token = re.search(r"uid=([^&]+)&token=(\S+)", mail.outbox[0].body).groups()

        res = self.client.post(
            reverse("password-reset-confirm"),
            {"uid": uid, "token": token, "new_password": "Nouveau-mdp-2026"},
        )
        self.assertEqual(res.status_code, 200)
        login = self.client.post(
            reverse("login"), {"email": "t@example.com", "password": "Nouveau-mdp-2026"}
        )
        self.assertEqual(login.status_code, 200)

    def test_unknown_email_gives_same_answer_and_no_mail(self):
        res = self.client.post(reverse("password-reset"), {"email": "nobody@example.com"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_bad_token_rejected(self):
        make_user()
        res = self.client.post(
            reverse("password-reset-confirm"),
            {"uid": "MQ", "token": "bad", "new_password": "Nouveau-mdp-2026"},
        )
        self.assertEqual(res.status_code, 400)


@override_settings(PRIVATE_MEDIA_ROOT=TMP_PRIVATE)
class IdentityVerificationTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_PRIVATE, ignore_errors=True)

    def upload(self, name="id.pdf"):
        return SimpleUploadedFile(name, b"%PDF-1.4 fake", content_type="application/pdf")

    def test_owner_uploads_identity_and_file_url_is_not_exposed(self):
        owner = make_user(email="o@example.com", role=User.Role.OWNER)
        self.client.force_authenticate(owner)
        res = self.client.post(reverse("identity"), {"document": self.upload()}, format="multipart")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "pending")
        self.assertNotIn("document", res.data)

    def test_second_upload_while_pending_conflicts(self):
        owner = make_user(email="o@example.com", role=User.Role.OWNER)
        self.client.force_authenticate(owner)
        self.client.post(reverse("identity"), {"document": self.upload()}, format="multipart")
        res = self.client.post(reverse("identity"), {"document": self.upload()}, format="multipart")
        self.assertEqual(res.status_code, 409)

    def test_bad_extension_rejected(self):
        owner = make_user(email="o@example.com", role=User.Role.OWNER)
        self.client.force_authenticate(owner)
        bad = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")
        res = self.client.post(reverse("identity"), {"document": bad}, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_tenant_cannot_upload_identity(self):
        self.client.force_authenticate(make_user())
        res = self.client.post(reverse("identity"), {"document": self.upload()}, format="multipart")
        self.assertEqual(res.status_code, 403)

    def test_document_view_admin_only_and_sandboxed(self):
        owner = make_user(email="o@example.com", role=User.Role.OWNER)
        v = IdentityVerification.objects.create(user=owner, document=self.upload())
        url = reverse("identity-document", args=[v.pk])

        self.client.force_login(owner)
        self.assertEqual(self.client.get(url).status_code, 302)  # renvoyé vers la connexion admin

        admin = User.objects.create_superuser(email="admin@example.com", password=PASSWORD)
        self.client.force_login(admin)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertEqual(res["X-Content-Type-Options"], "nosniff")
        self.assertIn("sandbox", res["Content-Security-Policy"])
        res.close()

    def test_is_identity_verified_after_approval(self):
        owner = make_user(email="o@example.com", role=User.Role.OWNER)
        IdentityVerification.objects.create(
            user=owner, document=self.upload(), status=IdentityVerification.Status.APPROVED
        )
        self.assertTrue(owner.is_identity_verified)
