from django.conf import settings
from .ai import initial_spec
from .generator import generate_preview
from .github import sync_project_repository


def provision_project(project):
    if not project.app_spec:
        project.app_spec = initial_spec(project.name, project.business_type, project.description, project.language)
    project.status = "building"
    project.save()
    root, checksum = generate_preview(project)
    project.status = "preview"
    project.last_build_error = ""
    project.save(update_fields=["status", "last_build_error", "app_spec", "updated_at"])
    if settings.GITHUB_TOKEN:
        sync_project_repository(project, root)
    return root, checksum
