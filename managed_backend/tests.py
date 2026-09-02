import json
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Organization, Project

from .models import AppFile, AppRecord


@override_settings(
    APP_PUBLIC_URL="https://studio.example.com",
    APP_ROOT_DOMAIN="studio.example.com",
    MANAGED_BACKEND_SIGNING_KEY="managed-test-secret",
)
class ManagedBackendAPITests(TestCase):
    def setUp(self):
        self.storage_temp = tempfile.TemporaryDirectory()
        self.storage_override = override_settings(
            APP_DATA_ROOT=Path(self.storage_temp.name),
            MANAGED_STORAGE_MAX_BYTES=1024 * 1024,
        )
        self.storage_override.enable()
        self.addCleanup(self.storage_override.disable)
        self.addCleanup(self.storage_temp.cleanup)

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
        self.storage_project = Project.objects.create(
            organization=organization,
            created_by=owner,
            name="Storage App",
            business_type="Services",
            description="Storage isolation test",
            status="preview",
            backend_features=["storage"],
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

    def test_storage_implicitly_activates_auth(self):
        response = self.client.get(
            reverse("managed_config", kwargs={"slug": self.storage_project.slug}),
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["features"], ["auth", "storage"])
        self.assertEqual(response.json()["storage"]["scope"], "owner")

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

    def test_managed_file_upload_download_and_owner_isolation(self):
        first_token = self.signup(project=self.storage_project, email="file-first@example.com")
        second_token = self.signup(project=self.storage_project, email="file-second@example.com")
        files_url = reverse("managed_files", kwargs={"slug": self.storage_project.slug})
        upload = SimpleUploadedFile("receipt.png", b"safe-image-bytes", content_type="image/png")
        created = self.client.post(
            files_url,
            {"file": upload},
            HTTP_AUTHORIZATION=f"Bearer {first_token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(created.status_code, 201, created.content)
        file_id = created.json()["file"]["id"]
        item = AppFile.objects.get(pk=file_id)
        stored_path = Path(self.storage_temp.name) / "managed-storage" / item.storage_key
        self.assertTrue(stored_path.is_file())
        self.assertEqual(item.owner.email, "file-first@example.com")

        download_url = reverse(
            "managed_file_download",
            kwargs={"slug": self.storage_project.slug, "file_id": file_id},
        )
        denied = self.client.get(
            download_url,
            HTTP_AUTHORIZATION=f"Bearer {second_token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(denied.status_code, 404)

        downloaded = self.client.get(
            download_url,
            HTTP_AUTHORIZATION=f"Bearer {first_token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(b"".join(downloaded.streaming_content), b"safe-image-bytes")
        self.assertIn("attachment", downloaded["Content-Disposition"])

    def test_active_content_upload_is_blocked(self):
        token = self.signup(project=self.storage_project, email="blocked@example.com")
        response = self.client.post(
            reverse("managed_files", kwargs={"slug": self.storage_project.slug}),
            {"file": SimpleUploadedFile("payload.svg", b"<svg><script/></svg>", content_type="image/svg+xml")},
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "file_type_blocked")
        self.assertEqual(AppFile.objects.count(), 0)

    def test_file_delete_removes_metadata_and_bytes(self):
        token = self.signup(project=self.storage_project, email="delete@example.com")
        created = self.client.post(
            reverse("managed_files", kwargs={"slug": self.storage_project.slug}),
            {"file": SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")},
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        file_id = created.json()["file"]["id"]
        item = AppFile.objects.get(pk=file_id)
        stored_path = Path(self.storage_temp.name) / "managed-storage" / item.storage_key
        response = self.client.delete(
            reverse("managed_file_detail", kwargs={"slug": self.storage_project.slug, "file_id": file_id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_ORIGIN="https://studio.example.com",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AppFile.objects.filter(pk=file_id).exists())
        self.assertFalse(stored_path.exists())

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
