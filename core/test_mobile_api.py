import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import Organization


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    APP_PUBLIC_URL="https://studio.aplus-solution.de",
)
class MobileApiTests(TestCase):
    def test_public_legal_pages_are_available(self):
        for path in ("/privacy/", "/terms/", "/support/", "/account-deletion/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_capacitor_preflight_is_allowed(self):
        response = self.client.options(
            "/api/mobile/login/",
            HTTP_ORIGIN="capacitor://localhost",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response["Access-Control-Allow-Origin"], "capacitor://localhost")

    def test_signup_me_and_in_app_account_deletion(self):
        signup = self.client.post(
            "/api/mobile/signup/",
            data=json.dumps({
                "email": "mobile@example.com",
                "password": "Strong-Mobile-Pass-2026!",
                "full_name": "Mobile Tester",
                "company_name": "Mobile Test GmbH",
            }),
            content_type="application/json",
            HTTP_ORIGIN="capacitor://localhost",
        )
        self.assertEqual(signup.status_code, 201, signup.content)
        token = signup.json()["token"]
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}", "HTTP_ORIGIN": "capacitor://localhost"}

        me = self.client.get("/api/mobile/me/", **headers)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["email"], "mobile@example.com")
        self.assertTrue(Organization.objects.filter(owner__email="mobile@example.com").exists())

        deleted = self.client.post(
            "/api/mobile/account/delete/",
            data=json.dumps({"confirmation": "DELETE"}),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(deleted.status_code, 200, deleted.content)
        self.assertFalse(get_user_model().objects.filter(email="mobile@example.com").exists())
