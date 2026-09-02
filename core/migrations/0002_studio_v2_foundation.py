from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="backend_features",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="project",
            name="builder_mode",
            field=models.CharField(
                choices=[("safe_pwa", "Safe PWA Builder"), ("code_agent", "Code Agent")],
                default="safe_pwa",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="source_imported_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="source_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="project",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("prompt", "Start from a prompt"),
                    ("github", "Import from GitHub"),
                    ("url", "Build from a website URL"),
                ],
                default="prompt",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="source_url",
            field=models.URLField(blank=True, max_length=1000),
        ),
        migrations.CreateModel(
            name="SandboxRun",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("kind", models.CharField(choices=[("import", "Import"), ("build", "Build"), ("test", "Test"), ("preview", "Preview")], default="build", max_length=16)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("starting", "Starting"), ("running", "Running"), ("success", "Success"), ("failed", "Failed"), ("blocked", "Blocked")], default="queued", max_length=16)),
                ("runtime", models.CharField(default="node20", max_length=80)),
                ("image", models.CharField(blank=True, max_length=255)),
                ("workspace_path", models.CharField(blank=True, max_length=500)),
                ("network_policy", models.CharField(default="restricted", max_length=32)),
                ("cpu_limit_millis", models.PositiveIntegerField(default=1000)),
                ("memory_limit_mb", models.PositiveIntegerField(default=768)),
                ("timeout_seconds", models.PositiveIntegerField(default=300)),
                ("command", models.JSONField(blank=True, default=list)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("log", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sandbox_runs", to="core.project")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"abstract": False},
        ),
    ]
