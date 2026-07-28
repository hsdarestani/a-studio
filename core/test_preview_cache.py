import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from .models import Organization, Project
from .services.ai import initial_spec
from .services.generator import generate_preview


User = get_user_model()
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class BuilderLayoutRegressionTests(SimpleTestCase):
    def test_composer_uses_a_shrinkable_chat_row(self):
        css = (REPOSITORY_ROOT / "static" / "builder-layout.css").read_text()
        self.assertIn("grid-template-rows:66px minmax(0,1fr) auto", css)
        self.assertIn(".chat-stream{min-height:0", css)
        self.assertIn(".builder-panel{height:100%;min-height:0;overflow:hidden", css)

    def test_embedded_preview_uses_cache_free_mode(self):
        template = (REPOSITORY_ROOT / "templates" / "project_detail.html").read_text()
        self.assertIn("?preview=1&amp;v={{ project.version }}", template)


class GeneratedPreviewCacheTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username="cache@example.com",
            email="cache@example.com",
            password="safe-password-123",
        )
        organization = Organization.objects.create(name="Cache GmbH", owner=user)
        self.project = Project.objects.create(
            organization=organization,
            created_by=user,
            name="Flavor Cache Test",
            business_type="Cosmetics",
            description="Interactive fragrance recommendations.",
            language="en",
            version=7,
            app_spec=initial_spec(
                "Flavor Cache Test",
                "Cosmetics",
                "Interactive fragrance recommendations.",
                "en",
            ),
        )

    def test_assets_are_versioned_and_cache_is_project_scoped(self):
        with tempfile.TemporaryDirectory() as temporary_root, override_settings(
            APP_DATA_ROOT=Path(temporary_root)
        ):
            root, _checksum = generate_preview(self.project)
            index = (root / "index.html").read_text()
            service_worker = (root / "sw.js").read_text()
            runtime = (root / "app.js").read_text()

        self.assertIn("styles.css?v=7", index)
        self.assertIn("config.js?v=7", index)
        self.assertIn("app.js?v=7", index)
        self.assertIn(f"astudio-{self.project.slug}-", index)
        self.assertIn(f"astudio-{self.project.slug}-v7", service_worker)
        self.assertIn("x.startsWith(P)", service_worker)
        self.assertIn("location.pathname.includes('/preview/')", runtime)
        self.assertIn("registration.unregister()", runtime)
