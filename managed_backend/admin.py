from django.contrib import admin

from .models import AppRecord, AppUser


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ("email", "project", "active", "last_login_at", "created_at")
    list_filter = ("active", "project")
    search_fields = ("email", "display_name", "project__name")
    readonly_fields = ("password_hash", "created_at", "updated_at", "last_login_at")
    ordering = ("-created_at",)


@admin.register(AppRecord)
class AppRecordAdmin(admin.ModelAdmin):
    list_display = ("project", "collection", "owner", "created_at", "updated_at")
    list_filter = ("collection", "project")
    search_fields = ("project__name", "owner__email", "collection")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
