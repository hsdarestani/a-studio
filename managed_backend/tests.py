import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Organization, Project

from .models import AppRecord


@override_settings(
    APP_PUBLIC_URL="https://studio.example.com",
    APP_ROOT_DOMAIN="studio.example.com",
    MANAGED_BACKEND_SIGNING_KEY="managed-test-secret",
)
class ManagedBackendAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        owner = User.objects.create_user(
            username="studio-owner@example.com",
            email="studio-owner@example.com",
            password="studio-owner-pass-123",
        )
        organization = Organization.objects.create(name="Managed Demo", owner=owner)
        self.project = Project.objects.create(
            organization=organization,
            created_by=owner,
            name="Managed App",
            business_type="Services",
            description="Managed backend test",
            status="preview",
            backend_features=["database"],
        )
        self.other_project = Project.objects.create(
            organization=organization,
            created_by=owner,
            name="Other Managed App",
            business_type="Services",
            description="Isolation test",
            status="preview",
            backend_features=["auth", "database"],
        )

    def post_json(self, url, payload, token="", origin="https://studio.example.com"):
        headers = {"HTTP_ORIGIN": origin}
        if token:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

    def signup(self, project=None, email="user@example.com"):
        project = project or self.project
        response = self.post_json(
            reverse("managed_signup", kwargs={"slug": project.slug}),
            {"email": email, "password": "correct-horse-123", "display_name": "Demo User"},
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["token"]

    def test_database_implicitly_activates_auth(self):
        response = self.client.get(
            reverse("managed_config", kwargs={"slug": self.project.slug}),
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["features"], ["auth", "database"])
        self.assertEqual(response["Access-Control-Allow-Origin"], "https://studio.example.com")

    def test_signup_login_and_me(self):
        token = self.signup()
        me = self.client.get(
            reverse("managed_me", kwargs={"slug": self.project.slug}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["email"], "user@example.com")

        login = self.post_json(
            reverse("managed_login", kwargs={"slug": self.project.slug}),
            {"email": "USER@example.com", "password": "correct-horse-123"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()["token"])

    def test_records_are_owner_scoped(self):
        first_token = self.signup(email="first@example.com")
        second_token = self.signup(email="second@example.com")
        list_url = reverse(
            "managed_records",
            kwargs={"slug": self.project.slug, "collection": "bookings"},
        )

        created = self.post_json(
            list_url,
            {"data": {"service": "Consultation", "date": "2026-09-03"}},
            token=first_token,
        )
        self.assertEqual(created.status_code, 201, created.content)
        record_id = created.json()["record"]["id"]
        self.assertEqual(AppRecord.objects.count(), 1)

        second_list = self.client.get(
            list_url,
            HTTP_AUTHORIZATION=f"Bearer {second_token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(second_list.status_code, 200)
        self.assertEqual(second_list.json()["records"], [])

        detail_url = reverse(
            "managed_record_detail",
            kwargs={
                "slug": self.project.slug,
                "collection": "bookings",
                "record_id": record_id,
            },
        )
        second_detail = self.client.get(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {second_token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(second_detail.status_code, 404)

        first_detail = self.client.get(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {first_token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(first_detail.status_code, 200)
        self.assertEqual(first_detail.json()["record"]["data"]["service"], "Consultation")

    def test_token_cannot_cross_project_boundary(self):
        token = self.signup()
        response = self.client.get(
            reverse("managed_me", kwargs={"slug": self.other_project.slug}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(response.status_code, 401)

    def test_untrusted_origin_does_not_receive_cors_permission(self):
        response = self.client.get(
            reverse("managed_config", kwargs={"slug": self.project.slug}),
            HTTP_ORIGIN="https://evil.example",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", response)

    def test_database_rejects_unauthenticated_write(self):
        response = self.post_json(
            reverse("managed_records", kwargs={"slug": self.project.slug, "collection": "forms"}),
            {"data": {"name": "Anonymous"}},
        )
        self.assertEqual(response.status_code, 401)
