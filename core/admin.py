from django.contrib import admin
from .models import AuditEvent, Conversation, CreditTransaction, Deployment, FeatureRequest, Membership, Message, Organization, Project, StoreSubmission


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "plan", "credits", "active", "created_at")
    search_fields = ("name", "slug", "billing_email")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "status", "language", "version", "updated_at")
    list_filter = ("status", "language", "business_type")
    search_fields = ("name", "slug", "description", "desired_domain")


admin.site.register(Membership)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(FeatureRequest)
admin.site.register(Deployment)
admin.site.register(CreditTransaction)
admin.site.register(AuditEvent)
admin.site.register(StoreSubmission)
