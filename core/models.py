import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organization(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_organizations")
    billing_email = models.EmailField(blank=True)
    plan = models.CharField(max_length=32, default="starter")
    credits = models.PositiveIntegerField(default=20)
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "workspace"
            candidate = base
            counter = 2
            while Organization.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base}-{counter}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Membership(TimeStampedModel):
    ROLE_CHOICES = [("owner", "Owner"), ("admin", "Admin"), ("member", "Member")]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="studio_memberships")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default="member")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "user"], name="unique_org_member")]


class Project(TimeStampedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("building", "Building"),
        ("preview", "Preview ready"),
        ("live", "Live"),
        ("paused", "Paused"),
        ("error", "Error"),
    ]
    BUILDER_MODE_CHOICES = [
        ("safe_pwa", "Safe PWA Builder"),
        ("code_agent", "Code Agent"),
    ]
    SOURCE_TYPE_CHOICES = [
        ("prompt", "Start from a prompt"),
        ("github", "Import from GitHub"),
        ("url", "Build from a website URL"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="projects")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_studio_projects")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    business_type = models.CharField(max_length=120)
    description = models.TextField()
    language = models.CharField(max_length=10, default="de")
    builder_mode = models.CharField(max_length=24, choices=BUILDER_MODE_CHOICES, default="safe_pwa")
    source_type = models.CharField(max_length=16, choices=SOURCE_TYPE_CHOICES, default="prompt")
    source_url = models.URLField(blank=True, max_length=1000)
    source_metadata = models.JSONField(default=dict, blank=True)
    source_imported_at = models.DateTimeField(null=True, blank=True)
    backend_features = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    app_spec = models.JSONField(default=dict, blank=True)
    repo_url = models.URLField(blank=True)
    repo_name = models.CharField(max_length=220, blank=True)
    desired_domain = models.CharField(max_length=255, blank=True)
    custom_domain = models.CharField(max_length=255, blank=True)
    preview_url = models.URLField(blank=True)
    live_url = models.URLField(blank=True)
    version = models.PositiveIntegerField(default=1)
    last_build_error = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or f"app-{str(self.id)[:8]}"
            candidate = base
            counter = 2
            while Project.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base}-{counter}"
                counter += 1
            self.slug = candidate
        if not self.desired_domain:
            self.desired_domain = f"{self.slug}.{settings.APP_ROOT_DOMAIN}"
        if not self.preview_url:
            self.preview_url = f"{settings.APP_PUBLIC_URL}/preview/{self.slug}/"
        if not self.live_url:
            self.live_url = f"{settings.APP_PUBLIC_URL}/apps/{self.slug}/"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Conversation(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="conversation")
    summary = models.TextField(blank=True)


class Message(TimeStampedModel):
    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant"), ("system", "System")]
    STATUS_CHOICES = [("queued", "Queued"), ("working", "Working"), ("done", "Done"), ("failed", "Failed")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    content = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="done")
    task_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]


class FeatureRequest(TimeStampedModel):
    SIZE_CHOICES = [("micro", "Micro"), ("small", "Small"), ("standard", "Standard"), ("advanced", "Advanced"), ("custom", "Custom")]
    STATUS_CHOICES = [("proposed", "Proposed"), ("approved", "Approved"), ("building", "Building"), ("done", "Done"), ("rejected", "Rejected"), ("failed", "Failed")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="feature_requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    title = models.CharField(max_length=220)
    description = models.TextField()
    size = models.CharField(max_length=16, choices=SIZE_CHOICES, default="small")
    credits = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="proposed")
    before_spec = models.JSONField(default=dict, blank=True)
    after_spec = models.JSONField(default=dict, blank=True)


class Deployment(TimeStampedModel):
    ENV_CHOICES = [("preview", "Preview"), ("production", "Production")]
    STATUS_CHOICES = [("queued", "Queued"), ("building", "Building"), ("success", "Success"), ("failed", "Failed"), ("rolled_back", "Rolled back")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="deployments")
    feature_request = models.ForeignKey(FeatureRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="deployments")
    environment = models.CharField(max_length=16, choices=ENV_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="queued")
    version = models.PositiveIntegerField(default=1)
    url = models.URLField(blank=True)
    log = models.TextField(blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    deployed_at = models.DateTimeField(null=True, blank=True)

    def mark_success(self, url, checksum=""):
        self.status = "success"
        self.url = url
        self.checksum = checksum
        self.deployed_at = timezone.now()
        self.save(update_fields=["status", "url", "checksum", "deployed_at", "updated_at"])


class CreditTransaction(TimeStampedModel):
    KIND_CHOICES = [("grant", "Grant"), ("purchase", "Purchase"), ("usage", "Usage"), ("refund", "Refund")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="credit_transactions")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    feature_request = models.ForeignKey(FeatureRequest, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    amount = models.IntegerField()
    balance_after = models.PositiveIntegerField()
    description = models.CharField(max_length=255)
    external_reference = models.CharField(max_length=255, blank=True)


class AuditEvent(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="audit_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class StoreSubmission(TimeStampedModel):
    PLATFORM_CHOICES = [("android", "Google Play"), ("ios", "Apple App Store"), ("both", "Both stores")]
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("eligibility", "Eligibility review"),
        ("accounts", "Waiting for developer accounts"),
        ("preparing", "Preparing package"),
        ("submitted", "Submitted"),
        ("review", "In store review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="store_submissions")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    platform = models.CharField(max_length=16, choices=PLATFORM_CHOICES, default="both")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="requested")
    notes = models.TextField(blank=True)
    eligibility_report = models.JSONField(default=dict, blank=True)
    quoted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    external_reference = models.CharField(max_length=255, blank=True)


class SandboxRun(TimeStampedModel):
    KIND_CHOICES = [
        ("import", "Import"),
        ("build", "Build"),
        ("test", "Test"),
        ("preview", "Preview"),
    ]
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("starting", "Starting"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("blocked", "Blocked"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sandbox_runs")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default="build")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="queued")
    runtime = models.CharField(max_length=80, default="node20")
    image = models.CharField(max_length=255, blank=True)
    workspace_path = models.CharField(max_length=500, blank=True)
    network_policy = models.CharField(max_length=32, default="restricted")
    cpu_limit_millis = models.PositiveIntegerField(default=1000)
    memory_limit_mb = models.PositiveIntegerField(default=768)
    timeout_seconds = models.PositiveIntegerField(default=300)
    command = models.JSONField(default=list, blank=True)
    result = models.JSONField(default=dict, blank=True)
    log = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
