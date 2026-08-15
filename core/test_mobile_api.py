import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import FeatureRequest, Message, Organization, Project


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

    def _signup(self):
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
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_ORIGIN": "capacitor://localhost",
        }
        return signup, headers

    def test_mobile_account_has_no_credit_or_plan_entitlements(self):
        signup, headers = self._signup()
        organization_payload = signup.json()["user"]["organization"]
        self.assertNotIn("credits", organization_payload)
        self.assertNotIn("plan", organization_payload)

        organization = Organization.objects.get(owner__email="mobile@example.com")
        self.assertEqual(organization.credits, 0)

        dashboard = self.client.get("/api/mobile/dashboard/", **headers)
        self.assertEqual(dashboard.status_code, 200)
        self.assertNotIn("credits", dashboard.json()["organization"])
        self.assertNotIn("plan", dashboard.json()["organization"])

    def test_mobile_project_is_coordination_only(self):
        _signup, headers = self._signup()
        created = self.client.post(
            "/api/mobile/projects/",
            data=json.dumps({
                "name": "Luna Booking",
                "business_type": "Salon",
                "description": "Coordinate the customer project.",
                "language": "de",
            }),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(created.status_code, 201, created.content)
        project_payload = created.json()["project"]
        project_id = project_payload["id"]
        self.assertEqual(project_payload["status"], "draft")
        self.assertNotIn("preview_url", project_payload)
        self.assertNotIn("live_url", project_payload)
        self.assertNotIn("repo_url", project_payload)
        self.assertNotIn("deployment", project_payload)

        project = Project.objects.get(pk=project_id)
        self.assertEqual(project.status, "draft")
        self.assertEqual(Message.objects.filter(conversation__project=project).count(), 0)

        request = self.client.post(
            f"/api/mobile/projects/{project_id}/chat/",
            data=json.dumps({"message": "Please move the appointment filter above the list."}),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(request.status_code, 201, request.content)
        self.assertEqual(FeatureRequest.objects.filter(project=project).count(), 1)
        feature = FeatureRequest.objects.get(project=project)
        self.assertEqual(feature.credits, 0)
        self.assertEqual(feature.status, "proposed")
        self.assertEqual(Message.objects.filter(conversation__project=project).count(), 0)

        detail = self.client.get(f"/api/mobile/projects/{project_id}/", **headers)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.json()["project"]["change_requests"]), 1)
        self.assertNotIn("preview_url", detail.json()["project"])

        publish = self.client.post(
            f"/api/mobile/projects/{project_id}/publish/",
            data="{}",
            content_type="application/json",
            **headers,
        )
        self.assertEqual(publish.status_code, 403)
        self.assertEqual(publish.json()["error"], "mobile_companion_only")

        store = self.client.post(
            f"/api/mobile/projects/{project_id}/store-submission/",
            data=json.dumps({"platform": "ios"}),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(store.status_code, 403)
        self.assertEqual(store.json()["error"], "mobile_companion_only")

    def test_signup_me_and_in_app_account_deletion(self):
        _signup, headers = self._signup()

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
