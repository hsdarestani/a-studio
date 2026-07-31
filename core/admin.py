from django.contrib import admin
from django.db import transaction
from .models import AuditEvent, Conversation, CreditTransaction, Deployment, FeatureRequest, Membership, Message, Organization, Project, StoreSubmission

admin.site.site_header = "A+ Studio Operations"
admin.site.site_title = "A+ Studio Operations"
admin.site.index_title = "Operations"


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "plan", "credits", "active", "created_at")
    search_fields = ("name", "slug", "billing_email")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "status", "language", "version", "updated_at")
    list_filter = ("status", "language", "business_type")
    search_fields = ("name", "slug", "description", "desired_domain")


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
