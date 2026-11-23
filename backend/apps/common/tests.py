"""Tests du endpoint de santé utilisé par le health check Render."""
from django.test import SimpleTestCase, override_settings


class HealthTests(SimpleTestCase):
    def test_health_is_public_json(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r"^api/health/$"])
    def test_health_is_exempt_from_ssl_redirect(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
