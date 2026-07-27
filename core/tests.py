import json
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from .models import Conversation, Membership, Organization, Project
from .services.ai import initial_spec, sanitize_spec
from .services.generator import generate_preview, publish_project
from .services.pricing import cost_for_size, estimate_size

User = get_user_model()


class GeneratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner@example.com", email="owner@example.com", password="safe-password-123")
        self.org = Organization.objects.create(name="Luna GmbH", owner=self.user)
        Membership.objects.create(organization=self.org, user=self.user, role="owner")
        self.project = Project.objects.create(
            organization=self.org,
            created_by=self.user,
            name="Luna Beauty",
            business_type="Beauty salon",
            description="Booking, services and loyalty for salon customers.",
            language="de",
            app_spec=initial_spec("Luna Beauty", "Beauty salon", "Booking, services and loyalty.", "de"),
        )
        Conversation.objects.create(project=self.project)

    def test_sanitize_rejects_executable_sections(self):
        spec = sanitize_spec({"sections": [{"type": "script", "text": "alert(1)"}, {"type": "about", "text": "Safe"}]})
        self.assertEqual([x["type"] for x in spec["sections"]], ["about"])

    def test_preview_and_publish_are_generated(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(APP_DATA_ROOT=Path(tmp)):
            root, checksum = generate_preview(self.project)
            self.assertTrue((root / "index.html").exists())
            self.assertTrue((root / "manifest.webmanifest").exists())
            self.assertGreater(len(checksum), 20)
            live, live_checksum = publish_project(self.project)
            self.assertTrue((live / "sw.js").exists())
            self.assertEqual(checksum, live_checksum)

    def test_manifest_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(APP_DATA_ROOT=Path(tmp)):
            root, _ = generate_preview(self.project)
            data = json.loads((root / "manifest.webmanifest").read_text())
            self.assertEqual(data["display"], "standalone")


class PricingTests(TestCase):
    def test_advanced_feature_cost(self):
        before = {"features": ["contact"], "sections": []}
        after = {"features": ["contact", "payments"], "sections": []}
        size = estimate_size(before, after)
        self.assertEqual(size, "advanced")
        self.assertEqual(cost_for_size(size), 7)
