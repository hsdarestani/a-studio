import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import ProjectCreateForm
from .models import Conversation, FeatureRequest, Membership, Organization, Project
from .services.code_workspace import CodeWorkspaceError, apply_changes, bootstrap_workspace, read_file


@override_settings(
    APP_PUBLIC_URL="https://studio.example.com",
    APP_ROOT_DOMAIN="studio.example.com",
    GITHUB_TOKEN="",
    CODE_AGENT_ENABLED=False,
    CODE_SANDBOX_ENDPOINT="",
    CODE_SANDBOX_SHARED_SECRET="",
)
class StudioV3CodeWorkspaceTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_override = override_settings(APP_DATA_ROOT=Path(self.temp.name))
        self.data_override.enable()
        self.addCleanup(self.data_override.disable)
        self.addCleanup(self.temp.cleanup)

        User = get_user_model()
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="pass-123456789",
        )
        self.outsider = User.objects.create_user(
            username="outside@example.com",
            email="outside@example.com",
            password="pass-123456789",
        )
        self.organization = Organization.objects.create(
            name="V3 Workspace",
            owner=self.owner,
            billing_email="owner@example.com",
            credits=50,
        )
        Membership.objects.create(organization=self.organization, user=self.owner, role="owner")
        self.project = Project.objects.create(
            organization=self.organization,
            created_by=self.owner,
            name="Code Demo",
            business_type="Services",
            description="A real code workspace",
            language="en",
            status="preview",
            builder_mode="code_agent",
            source_type="prompt",
        )
        Conversation.objects.create(project=self.project)
        self.safe_project = Project.objects.create(
            organization=self.organization,
            created_by=self.owner,
            name="Safe Demo",
            business_type="Services",
            description="Safe builder",
            language="en",
            status="preview",
            builder_mode="safe_pwa",
            source_type="prompt",
        )
        Conversation.objects.create(project=self.safe_project)

    def test_code_agent_is_selectable_without_external_sandbox(self):
        form = ProjectCreateForm(
            data={
                "name": "New Code App",
                "business_type": "Clinic",
                "description": "Build a booking app",
                "language": "en",
                "source_type": "prompt",
                "source_url": "",
                "builder_mode": "code_agent",
                "backend_features": ["auth", "database"],
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["builder_mode"], "code_agent")
        self.assertIn(("code_agent", "Code Agent V3 — real code workspace"), list(form.fields["builder_mode"].choices))

    def test_workspace_bootstraps_real_files(self):
        root = bootstrap_workspace(self.project)
        self.assertTrue((root / "index.html").is_file())
        self.assertTrue((root / "styles.css").is_file())
        self.assertTrue((root / "app.js").is_file())
        path, content = read_file(self.project, "index.html")
        self.assertEqual(path, "index.html")
        self.assertIn("Code Demo", content)

    def test_workspace_rejects_traversal_and_unsafe_code(self):
        with self.assertRaises(CodeWorkspaceError):
            apply_changes(self.project, [{"path": "../escape.js", "content": "console.log(1)"}])
        with self.assertRaises(CodeWorkspaceError):
            apply_changes(self.project, [{"path": "app.js", "content": "eval('2+2')"}])

    def test_code_ide_requires_membership_and_code_mode(self):
        self.client.force_login(self.outsider)
        denied = self.client.get(reverse("code_manifest", kwargs={"pk": self.project.id}))
        self.assertEqual(denied.status_code, 404)

        self.client.force_login(self.owner)
        safe = self.client.get(reverse("code_manifest", kwargs={"pk": self.safe_project.id}))
        self.assertEqual(safe.status_code, 404)
        code = self.client.get(reverse("code_manifest", kwargs={"pk": self.project.id}))
        self.assertEqual(code.status_code, 200)
        self.assertEqual(code.json()["entry"], "index.html")

    def test_manual_code_save_versions_and_rebuilds_preview(self):
        bootstrap_workspace(self.project)
        self.client.force_login(self.owner)
        url = reverse("code_file_save", kwargs={"pk": self.project.id})
        response = self.client.post(
            url,
            data=json.dumps({"path": "styles.css", "content": "body { color: rgb(1, 2, 3); }"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.project.refresh_from_db()
        self.assertEqual(self.project.version, 2)
        self.assertEqual(self.project.status, "preview")
        preview_css = Path(self.temp.name) / "preview" / self.project.slug / "styles.css"
        self.assertEqual(preview_css.read_text(encoding="utf-8"), "body { color: rgb(1, 2, 3); }")
        feature = FeatureRequest.objects.filter(project=self.project).latest("created_at")
        self.assertEqual(feature.credits, 0)
        self.assertEqual(feature.status, "done")
        self.assertEqual(feature.after_spec["changed_files"], ["styles.css"])

    def test_code_diff_is_available_after_manual_edit(self):
        bootstrap_workspace(self.project)
        self.client.force_login(self.owner)
        save = self.client.post(
            reverse("code_file_save", kwargs={"pk": self.project.id}),
            data=json.dumps({"path": "app.js", "content": "console.log('v3');"}),
            content_type="application/json",
        )
        self.assertEqual(save.status_code, 200, save.content)
        feature_id = save.json()["feature_id"]
        diff = self.client.get(reverse("code_diff", kwargs={"pk": self.project.id, "feature_id": feature_id}))
        self.assertEqual(diff.status_code, 200, diff.content)
        self.assertIn("app.js", diff.json()["diff"])
        self.assertIn("console.log('v3');", diff.json()["diff"])

    @patch("core.workflow_views.process_code_chat_message.delay")
    @patch("core.workflow_views.process_chat_message.delay")
    def test_chat_routes_code_projects_to_v3_task(self, safe_delay, code_delay):
        code_delay.return_value.id = "code-task-1"
        safe_delay.return_value.id = "safe-task-1"
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("chat_submit", kwargs={"pk": self.project.id}),
            {"message": "Move the primary CTA into the hero."},
        )
        self.assertEqual(response.status_code, 200, response.content)
        code_delay.assert_called_once()
        safe_delay.assert_not_called()
