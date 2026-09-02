from celery import shared_task
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from .models import AuditEvent, Deployment, Message, Project
from .services.ai import propose_change
from .services.provisioning import provision_project
from .services.sandbox import dispatch_code_agent
from .services.source_import import SourceImportError, context_for_prompt, import_source_context


def _project_language(project):
    return project.language if project.language in {"de", "en"} else "de"


def _backend_requirements(project):
    features = [str(item) for item in (project.backend_features or []) if item]
    if not features:
        return ""
    return "Requested backend capabilities: " + ", ".join(features) + ". Design the product architecture and user flows for these capabilities."


def _build_instructions(project, metadata):
    imported_context = context_for_prompt(metadata)
    mode_instruction = (
        "Create the complete first version as a real code project. Use a maintainable application structure, validate the build and return a preview URL through the sandbox callback."
        if project.builder_mode == "code_agent"
        else f"Create the complete first version of this PWA for a {project.business_type} business."
    )
    prompt_parts = [
        mode_instruction,
        f"Business type: {project.business_type}",
        f"Requirements: {project.description}",
        _backend_requirements(project),
    ]
    if imported_context:
        prompt_parts.append(
            "Use the following imported source as reference. Preserve useful product structure and business information. Never expose secrets, tokens or private configuration:\n"
            + imported_context
        )
    return "\n\n".join(part for part in prompt_parts if part)


@shared_task(bind=True)
def import_and_provision_initial_project(self, project_id):
    project = Project.objects.select_related("organization", "created_by").get(pk=project_id)
    deployment = Deployment.objects.create(
        project=project,
        environment="preview",
        status="building",
        version=project.version,
        url=project.preview_url,
    )
    try:
        try:
            metadata = import_source_context(project)
            project.source_metadata = metadata
            project.source_imported_at = timezone.now()
            project.save(update_fields=["source_metadata", "source_imported_at", "updated_at"])
            AuditEvent.objects.create(
                organization=project.organization,
                user=project.created_by,
                project=project,
                action="project_source_imported",
                payload={"source_type": project.source_type, "source_url": project.source_url},
            )
        except SourceImportError:
            if project.source_type != "prompt":
                raise
            metadata = {"source_type": "prompt"}

        instructions = _build_instructions(project, metadata)

        if project.builder_mode == "code_agent":
            project.status = "building"
            project.save(update_fields=["status", "updated_at"])
            run = dispatch_code_agent(
                project=project,
                requested_by=project.created_by,
                instructions=instructions,
                deployment_id=deployment.id,
            )
            with translation.override(_project_language(project)):
                Message.objects.create(
                    conversation=project.conversation,
                    role="assistant",
                    content=_("Code Agent is building this project inside the isolated sandbox. Production is untouched while the build, tests and preview are prepared."),
                    metadata={
                        "action": "code_agent_running",
                        "sandbox_run_id": str(run.id),
                        "source_type": project.source_type,
                        "backend_features": project.backend_features,
                    },
                )
            return {"status": "sandbox_running", "sandbox_run_id": str(run.id)}

        result = propose_change(project, instructions, [])
        if result.get("action") == "apply":
            project.app_spec = result["spec"]
            project.save(update_fields=["app_spec", "updated_at"])

        _root, checksum = provision_project(project)
        deployment.mark_success(project.preview_url, checksum)
        with translation.override(_project_language(project)):
            source_note = ""
            if project.source_type == "github":
                source_note = _(" I also imported the repository context before building the preview.")
            elif project.source_type == "url":
                source_note = _(" I also analyzed the source website before building the preview.")
            content = _(
                "Your first PWA is ready. Open the preview and tell me what you would like to change. "
                "I can update the structure, text, colors, modules, forms, booking experience, products, loyalty and more."
            ) + source_note
        Message.objects.create(
            conversation=project.conversation,
            role="assistant",
            content=content,
            metadata={
                "preview_url": project.preview_url,
                "deployment_id": str(deployment.id),
                "source_type": project.source_type,
                "backend_features": project.backend_features,
            },
        )
        return {"status": "success", "preview_url": project.preview_url}
    except Exception as exc:
        project.status = "error"
        project.last_build_error = str(exc)
        project.save(update_fields=["status", "last_build_error", "updated_at"])
        deployment.status = "failed"
        deployment.log = str(exc)
        deployment.save(update_fields=["status", "log", "updated_at"])
        with translation.override(_project_language(project)):
            Message.objects.create(
                conversation=project.conversation,
                role="assistant",
                status="failed",
                content=_("The first build could not be completed safely. The source import or isolated build log needs review."),
                metadata={"error": str(exc)[:1000], "source_type": project.source_type},
            )
        raise
