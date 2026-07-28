import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Conversation, Membership, Organization, Project
from .services.ai import initial_spec, propose_change, sanitize_spec
from .services.generator import generate_preview, publish_project
from .services.pricing import cost_for_size, estimate_size

User = get_user_model()


class GeneratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="safe-password-123",
        )
        self.org = Organization.objects.create(name="Luna GmbH", owner=self.user)
        Membership.objects.create(
            organization=self.org,
            user=self.user,
            role="owner",
        )
        self.project = Project.objects.create(
            organization=self.org,
            created_by=self.user,
            name="Luna Beauty",
            business_type="Beauty salon",
            description="Booking, services and loyalty for salon customers.",
            language="de",
            app_spec=initial_spec(
                "Luna Beauty",
                "Beauty salon",
                "Booking, services and loyalty.",
                "de",
            ),
        )
        Conversation.objects.create(project=self.project)

    def test_sanitize_rejects_executable_sections(self):
        spec = sanitize_spec(
            {
                "sections": [
                    {"type": "script", "text": "alert(1)"},
                    {"type": "about", "text": "Safe"},
                ]
            }
        )
        self.assertEqual([item["type"] for item in spec["sections"]], ["about"])

    def test_preview_and_publish_are_generated(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(
            APP_DATA_ROOT=Path(tmp)
        ):
            root, checksum = generate_preview(self.project)
            self.assertTrue((root / "index.html").exists())
            self.assertTrue((root / "manifest.webmanifest").exists())
            self.assertGreater(len(checksum), 20)
            live, live_checksum = publish_project(self.project)
            self.assertTrue((live / "sw.js").exists())
            self.assertEqual(checksum, live_checksum)

    def test_manifest_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(
            APP_DATA_ROOT=Path(tmp)
        ):
            root, _ = generate_preview(self.project)
            data = json.loads((root / "manifest.webmanifest").read_text())
            self.assertEqual(data["display"], "standalone")

    def test_recommendation_quiz_preserves_nested_scores(self):
        spec = sanitize_spec(
            {
                "app": {"title": "Flavor", "language": "en"},
                "sections": [
                    {
                        "type": "recommendation_quiz",
                        "title": "Scent identity",
                        "questions": [
                            {
                                "id": "mood",
                                "prompt": "Choose a mood",
                                "options": [
                                    {
                                        "label": "Fresh",
                                        "emoji": "🌊",
                                        "scores": {"fresh": 3, "woody": 1},
                                    }
                                ],
                            }
                        ],
                        "catalog": [
                            {
                                "brand": "Maison Test",
                                "model": "Azure",
                                "traits": {"fresh": 5, "woody": 1},
                            }
                        ],
                    }
                ],
            }
        )

        quiz = spec["sections"][0]
        self.assertEqual(quiz["type"], "recommendation_quiz")
        self.assertEqual(
            quiz["questions"][0]["options"][0]["scores"]["fresh"],
            3,
        )
        self.assertEqual(quiz["catalog"][0]["traits"]["fresh"], 5)

    def test_interactive_recommendation_runtime_is_generated(self):
        self.project.app_spec = sanitize_spec(
            {
                "app": {
                    "title": "Flavor",
                    "tagline": "Find your scent identity.",
                    "language": "en",
                },
                "sections": [
                    {
                        "type": "hero",
                        "title": "Meet your signature scent",
                        "text": "A playful fragrance discovery experience.",
                    },
                    {
                        "type": "recommendation_quiz",
                        "title": "Scent identity quiz",
                        "xp_per_answer": 100,
                        "questions": [
                            {
                                "id": "energy",
                                "prompt": "Pick your energy",
                                "options": [
                                    {
                                        "label": "Bright",
                                        "emoji": "☀️",
                                        "scores": {"fresh": 4},
                                    }
                                ],
                            }
                        ],
                        "catalog": [
                            {
                                "brand": "Maison Test",
                                "model": "Azure",
                                "traits": {"fresh": 5},
                            }
                        ],
                    },
                ],
            }
        )
        self.project.save(update_fields=["app_spec", "updated_at"])

        with tempfile.TemporaryDirectory() as tmp, override_settings(
            APP_DATA_ROOT=Path(tmp)
        ):
            root, _ = generate_preview(self.project)
            javascript = (root / "app.js").read_text()
            configuration = (root / "config.js").read_text()

        self.assertIn("function calculateResults", javascript)
        self.assertIn("localStorage.setItem", javascript)
        self.assertIn("data-favorite", javascript)
        self.assertIn('"type": "recommendation_quiz"', configuration)
        self.assertIn('"fresh": 4', configuration)

    def test_project_status_returns_current_build_and_repository_state(self):
        self.project.status = "preview"
        self.project.version = 2
        self.project.repo_name = "astudio-app-luna"
        self.project.repo_url = "https://github.com/example/astudio-app-luna"
        self.project.save(
            update_fields=[
                "status",
                "version",
                "repo_name",
                "repo_url",
                "updated_at",
            ]
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("project_status", args=[self.project.id]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "preview")
        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["repo_name"], "astudio-app-luna")
        self.assertEqual(payload["credits"], self.org.credits)

    @override_settings(
        OPENAI_API_KEY="test-key",
        OPENAI_MODEL="blocked-model",
        OPENAI_FALLBACK_MODELS=["working-model"],
    )
    @patch("core.services.ai.OpenAI")
    def test_model_access_error_uses_configured_fallback(self, openai_class):
        response = Mock(
            output_text=json.dumps(
                {
                    "action": "apply",
                    "message": "Updated safely.",
                    "feature_title": "Fallback update",
                    "feature_description": "Uses an accessible model.",
                    "spec": self.project.app_spec,
                }
            )
        )
        client = Mock()
        client.responses.create.side_effect = [
            Exception("model_not_found: organization must be verified"),
            response,
        ]
        openai_class.return_value = client

        result = propose_change(self.project, "Update the app", [])

        self.assertEqual(result["action"], "apply")
        self.assertEqual(client.responses.create.call_count, 2)
        self.assertEqual(
            client.responses.create.call_args_list[0].kwargs["model"],
            "blocked-model",
        )
        self.assertEqual(
            client.responses.create.call_args_list[1].kwargs["model"],
            "working-model",
        )


class PricingTests(TestCase):
    def test_advanced_feature_cost(self):
        before = {"features": ["contact"], "sections": []}
        after = {"features": ["contact", "payments"], "sections": []}
        size = estimate_size(before, after)
        self.assertEqual(size, "advanced")
        self.assertEqual(cost_for_size(size), 7)


class SignupTests(TestCase):
    def test_email_signup_logs_in_with_multiple_auth_backends(self):
        response = self.client.post(
            reverse("signup"),
            {
                "full_name": "Max Mustermann",
                "email": "max@example.com",
                "company_name": "Muster GmbH",
                "password1": "A-very-safe-password-2026!",
                "password2": "A-very-safe-password-2026!",
            },
        )

        self.assertRedirects(
            response,
            reverse("project_create"),
            fetch_redirect_response=False,
        )
        user = User.objects.get(email="max@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertEqual(
            self.client.session["_auth_user_backend"],
            "django.contrib.auth.backends.ModelBackend",
        )
        organization = Organization.objects.get(owner=user)
        self.assertEqual(organization.credits, 20)
        self.assertTrue(
            Membership.objects.filter(
                organization=organization,
                user=user,
                role="owner",
            ).exists()
        )
