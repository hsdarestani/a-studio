from django.contrib import admin
from django.db import transaction
from .models import AuditEvent, Conversation, CreditTransaction, Deployment, FeatureRequest, Membership, Message, Organization, Project, SandboxRun, StoreSubmission

admin.site.site_header = "A+ Studio Operations"
admin.site.site_title = "A+ Studio Operations"
admin.site.index_title = "Operations"


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "plan", "credits", "active", "created_at")
    search_fields = ("name", "slug", "billing_email")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "status", "builder_mode", "source_type", "language", "version", "updated_at")
    list_filter = ("status", "builder_mode", "source_type", "language", "business_type")
    search_fields = ("name", "slug", "description", "source_url", "desired_domain")


@admin.register(SandboxRun)
class SandboxRunAdmin(admin.ModelAdmin):
    list_display = ("project", "kind", "status", "runtime", "memory_limit_mb", "timeout_seconds", "created_at")
    list_filter = ("status", "kind", "runtime", "network_policy")
    search_fields = ("project__name", "workspace_path", "log")
    readonly_fields = ("created_at", "updated_at", "started_at", "finished_at")
    ordering = ("-created_at",)


@admin.register(StoreSubmission)
class StoreSubmissionAdmin(admin.ModelAdmin):
    list_display = ("project", "platform", "status", "requested_by", "quoted_price", "created_at", "updated_at")
    list_filter = ("status", "platform", "created_at")
    search_fields = ("project__name", "project__organization__name", "requested_by__email", "external_reference")
    list_select_related = ("project", "project__organization", "requested_by")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change and obj.pk:
            previous_status = StoreSubmission.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
        super().save_model(request, obj, form, change)
        if change and previous_status != obj.status:
            from .tasks import notify_store_submission_status
            transaction.on_commit(lambda: notify_store_submission_status.delay(str(obj.pk)), robust=True)


admin.site.register(Membership)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(FeatureRequest)
admin.site.register(Deployment)
admin.site.register(CreditTransaction)
admin.site.register(AuditEvent)
