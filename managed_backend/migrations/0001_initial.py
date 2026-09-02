import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0002_studio_v2_foundation"),
    ]

    operations = [
        migrations.CreateModel(
            name="AppUser",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254)),
                ("password_hash", models.CharField(max_length=255)),
                ("display_name", models.CharField(blank=True, max_length=160)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("active", models.BooleanField(default=True)),
                ("last_login_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="managed_users", to="core.project")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["project", "active"], name="mb_user_project_active_idx")],
                "constraints": [models.UniqueConstraint(fields=("project", "email"), name="unique_managed_user_email_per_project")],
            },
        ),
        migrations.CreateModel(
            name="AppRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("collection", models.SlugField(max_length=80)),
                ("data", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="records", to="managed_backend.appuser")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="managed_records", to="core.project")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["project", "collection", "owner", "-created_at"], name="mb_record_owner_collection_idx")],
            },
        ),
    ]
