import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class AppUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("core.Project", on_delete=models.CASCADE, related_name="managed_users")
    email = models.EmailField(max_length=254)
    password_hash = models.CharField(max_length=255)
    display_name = models.CharField(max_length=160, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "email"], name="unique_managed_user_email_per_project")
        ]
        indexes = [
            models.Index(fields=["project", "active"], name="mb_user_project_active_idx"),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def mark_login(self):
        self.last_login_at = timezone.now()
        self.save(update_fields=["last_login_at", "updated_at"])

    def __str__(self):
        return f"{self.email} · {self.project}"


class AppRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("core.Project", on_delete=models.CASCADE, related_name="managed_records")
    owner = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="records")
    collection = models.SlugField(max_length=80)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["project", "collection", "owner", "-created_at"],
                name="mb_record_owner_collection_idx",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project}:{self.collection}:{self.id}"
