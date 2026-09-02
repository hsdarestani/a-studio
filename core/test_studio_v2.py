import hashlib
import hmac

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .forms import ProjectCreateForm
from .models import Organization, Project, SandboxRun
from .services.sandbox import sandbox_ready, verify_signature
from .services.source_import import SourceImportError, normalize_source_url


class SourceImportSafetyTests(TestCase):
    def test_github_repository_url_is_canonicalized(self):
        self.assertEqual(
            normalize_source_url("https://github.com/hsdarestani/a-studio.git", "github"),
            "https://github.com/hsdarestani/a-studio",
        )

    def test_github_mode_rejects_non_github_host(self):
        with self.assertRaises(SourceImportError):
            normalize_source_url("https://example.com/owner/repo", "github")

    def test_url_import_rejects_localhost(self):
        with self.assertRaises(SourceImportError):
            normalize_source_url("http://localhost:9000/admin", "url")

    def test_prompt_project_form_does_not_require_source_url(self):
        form = ProjectCreateForm(
            data={
                "name": "Demo",
                "business_type": "Retail",
                "description": "A useful customer app",
                "language": "de",
                "source_type": "prompt",
                "source_url": "",
                "builder_mode": "safe_pwa",
                "backend_features": ["auth", "database"],
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["backend_features"], ["auth", "database"])

    def test_legacy_project_payload_gets_v2_defaults(self):
        form = ProjectCreateForm(
            data={
                "name": "Legacy Demo",
                "business_type": "Services",
                "description": "Created by an older companion client",
                "language": "de",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["source_type"], "prompt")
        self.assertEqual(form.cleaned_data["builder_mode"], "safe_pwa")
        self.assertEqual(form.cleaned_data["source_url"], "")


class StudioV2ModelTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="owner@example.com", email="owner@example.com", password="test-pass-123")
        self.organization = Organization.objects.create(name="Demo GmbH", owner=self.user)

    def test_project_defaults_to_safe_builder(self):
        project = Project.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Demo App",
            business_type="Services",
            description="Demo",
        )
        self.assertEqual(project.builder_mode, "safe_pwa")
        self.assertEqual(project.source_type, "prompt")
        self.assertEqual(project.backend_features, [])

    def test_sandbox_run_has_restricted_defaults(self):
        project = Project.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Code Demo",
            business_type="Software",
            description="Demo",
        )
        run = SandboxRun.objects.create(project=project, requested_by=self.user)
        self.assertEqual(run.network_policy, "restricted")
        self.assertEqual(run.memory_limit_mb, 768)
        self.assertEqual(run.timeout_seconds, 300)


@override_settings(
    CODE_AGENT_ENABLED=True,
    CODE_SANDBOX_ENDPOINT="https://sandbox.example.com",
    CODE_SANDBOX_SHARED_SECRET="shared-test-secret",
)
class SandboxSignatureTests(TestCase):
    def test_sandbox_is_ready_only_with_all_configuration(self):
        self.assertTrue(sandbox_ready())

    def test_signed_callback_body_is_verified(self):
        raw = b'{"status":"success"}'
        digest = hmac.new(b"shared-test-secret", raw, hashlib.sha256).hexdigest()
        self.assertTrue(verify_signature(raw, f"sha256={digest}"))
        self.assertFalse(verify_signature(raw, "sha256=deadbeef"))
