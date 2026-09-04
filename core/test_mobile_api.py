import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import FeatureRequest, Membership, Organization, Project


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    APP_PUBLIC_URL="https://studio.aplus-solution.de",
)
class MobileApiTests(TestCase):
    def test_public_legal_pages_are_available(self):
        for path in (
            "/privacy/", "/terms/", "/support/", "/account-deletion/",
            "/mobile/", "/mobile/privacy/", "/mobile/terms/", "/mobile/support/",
        ):
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

    def _existing_account(self, *, project_status="building"):
        user = get_user_model().objects.create_user(
            username="mobile@example.com",
            email="mobile@example.com",
            password="Strong-Mobile-Pass-2026!",
            first_name="Mobile",
            last_name="Tester",
        )
        organization = Organization.objects.create(
            name="Existing Customer GmbH",
            owner=user,
            billing_email=user.email,
            credits=0,
        )
        Membership.objects.create(organization=organization, user=user, role="owner")
        project = Project.objects.create(
            organization=organization,
            created_by=user,
            name="Existing App",
            business_type="Customer service",
            description="An existing app project.",
            language="de",
            status=project_status,
        )
        login = self.client.post(
            "/api/mobile/login/",
            data=json.dumps({"email": user.email, "password": "Strong-Mobile-Pass-2026!"}),
            content_type="application/json",
            HTTP_ORIGIN="capacitor://localhost",
        )
        self.assertEqual(login.status_code, 200, login.content)
        token = login.json()["token"]
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_ORIGIN": "capacitor://localhost",
        }
        return user, organization, project, headers

    def test_mobile_registration_stays_disabled(self):
        signup = self.client.post(
            "/api/mobile/signup/",
            data=json.dumps({"email": "new@example.com", "password": "Strong-Mobile-Pass-2026!"}),
            content_type="application/json",
        )
        self.assertEqual(signup.status_code, 403)
        self.assertEqual(signup.json()["error"], "mobile_existing_accounts_only")

    @patch("core.mobile_api.provision_initial_project.delay")
    def test_mobile_can_create_cloud_app_without_exposing_executable_preview(self, enqueue):
        _user, organization, _project, headers = self._existing_account()
        created = self.client.post(
            "/api/mobile/projects/",
            data=json.dumps({
                "name": "Luna Booking",
                "business_type": "Salon",
                "description": "Create a booking app with weekly appointments.",
                "language": "de",
            }),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(created.status_code, 201, created.content)
        payload = created.json()["project"]
        self.assertEqual(payload["status"], "queued")
        self.assertEqual(payload["name"], "Luna Booking")
        enqueue.assert_called_once()

        project = Project.objects.get(pk=payload["id"])
        self.assertEqual(project.builder_mode, "safe_pwa")
        self.assertEqual(project.source_type, "prompt")
        self.assertEqual(project.source_url, "")
        self.assertEqual(project.organization, organization)

        for forbidden in ("preview_url", "live_url", "repo_url", "deployment", "store_submissions"):
            self.assertNotIn(forbidden, payload)

    def test_mobile_payload_and_requests_keep_cloud_execution_boundary(self):
        _user, organization, project, headers = self._existing_account(project_status="preview")

        dashboard = self.client.get("/api/mobile/dashboard/", **headers)
        self.assertEqual(dashboard.status_code, 200)
        self.assertNotIn("credits", dashboard.json()["organization"])
        self.assertNotIn("plan", dashboard.json()["organization"])
        self.assertEqual(dashboard.json()["projects"][0]["status"], "generated")

        request = self.client.post(
            f"/api/mobile/projects/{project.id}/chat/",
            data=json.dumps({"message": "Add a clearer weekly booking flow."}),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(request.status_code, 201, request.content)
        self.assertEqual(FeatureRequest.objects.filter(project=project).count(), 1)

        detail = self.client.get(f"/api/mobile/projects/{project.id}/", **headers)
        self.assertEqual(detail.status_code, 200)
        payload = detail.json()["project"]
        self.assertEqual(payload["status"], "generated")
        self.assertEqual(len(payload["requests"]), 1)
        for forbidden in ("preview_url", "live_url", "repo_url", "deployment", "store_submissions"):
            self.assertNotIn(forbidden, payload)

        config = self.client.get("/api/mobile/config/")
        self.assertEqual(config.status_code, 200)
        self.assertEqual(config.json()["mode"], "cloud_app_builder")
        capabilities = config.json()["capabilities"]
        self.assertTrue(capabilities["existing_account_access"])
        self.assertTrue(capabilities["project_creation"])
        self.assertTrue(capabilities["cloud_app_generation"])
        self.assertFalse(capabilities["account_registration"])
        self.assertFalse(capabilities["code_download"])
        self.assertFalse(capabilities["local_code_execution"])
        self.assertFalse(capabilities["external_app_preview"])
        self.assertFalse(capabilities["store_status"])
        self.assertFalse(capabilities["mobile_publishing"])
        self.assertFalse(capabilities["mobile_purchases"])

        organization.refresh_from_db()
        self.assertEqual(organization.credits, 0)

    def test_me_and_in_app_account_deletion(self):
        user, _organization, _project, headers = self._existing_account()

        me = self.client.get("/api/mobile/me/", **headers)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["email"], "mobile@example.com")

        deleted = self.client.post(
            "/api/mobile/account/delete/",
            data=json.dumps({"confirmation": "DELETE"}),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(deleted.status_code, 200, deleted.content)
        self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())
