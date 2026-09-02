import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("managed_backend", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AppFile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("storage_key", models.CharField(max_length=500, unique=True)),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=160)),
                ("size", models.PositiveBigIntegerField()),
                ("sha256", models.CharField(max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="files", to="managed_backend.appuser")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="managed_files", to="core.project")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["project", "owner", "-created_at"], name="mb_file_owner_created_idx")],
            },
        ),
    ]
