from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from .models import CreditTransaction, Deployment, FeatureRequest, Message, Project
from .services.ai import propose_change
from .services.generator import generate_preview, publish_project
from .services.github import sync_project_repository
from .services.pricing import cost_for_size, estimate_size
from .services.provisioning import provision_project


def _project_language(project):
    return project.language if project.language in {"de", "en"} else "de"


@shared_task(bind=True)
def provision_initial_project(self, project_id):
    project = Project.objects.get(pk=project_id)
    deployment = Deployment.objects.create(project=project, environment="preview", status="building", version=project.version, url=project.preview_url)
    try:
        try:
            result = propose_change(
                project,
                f"Create the complete first version of this PWA for a {project.business_type} business. Requirements: {project.description}",
                [],
            )
            if result.get("action") == "apply":
                project.app_spec = result["spec"]
                project.save(update_fields=["app_spec", "updated_at"])
        except Exception:
            pass
        _root, checksum = provision_project(project)
        deployment.mark_success(project.preview_url, checksum)
        with translation.override(_project_language(project)):
            content = _(
                "Your first PWA is ready. Open the preview and tell me what you would like to change. "
                "I can update the structure, text, colors, modules, forms, booking experience, products, loyalty and more."
            )
        Message.objects.create(
            conversation=project.conversation,
            role="assistant",
            content=content,
            metadata={"preview_url": project.preview_url, "deployment_id": str(deployment.id)},
        )
        return {"status": "success", "preview_url": project.preview_url}
    except Exception as exc:
        project.status = "error"
        project.last_build_error = str(exc)
        project.save(update_fields=["status", "last_build_error", "updated_at"])
        deployment.status = "failed"
        deployment.log = str(exc)
        deployment.save(update_fields=["status", "log", "updated_at"])
        raise


@shared_task(bind=True)
def process_chat_message(self, user_message_id, assistant_message_id, user_id):
    user_message = Message.objects.select_related("conversation__project__organization").get(pk=user_message_id)
    assistant = Message.objects.get(pk=assistant_message_id)
    project = user_message.conversation.project
    assistant.status = "working"
    assistant.save(update_fields=["status", "updated_at"])
    try:
        history = list(user_message.conversation.messages.exclude(pk=assistant.pk).values("role", "content"))
        result = propose_change(project, user_message.content, history)
        if result["action"] == "clarify":
            assistant.content = result["message"]
            assistant.status = "done"
            assistant.metadata = {"action": "clarify"}
            assistant.save(update_fields=["content", "status", "metadata", "updated_at"])
            return {"status": "clarify"}

        before = project.app_spec or {}
        after = result["spec"]
        size = estimate_size(before, after)
        cost = cost_for_size(size)

        with transaction.atomic():
            locked_project = Project.objects.select_for_update().select_related("organization").get(pk=project.pk)
            organization = locked_project.organization
            feature = FeatureRequest.objects.create(
                project=locked_project,
                requested_by_id=user_id,
                title=result["feature_title"],
                description=result["feature_description"],
                size=size,
                credits=cost,
                status="building" if organization.credits >= cost else "proposed",
                before_spec=before,
                after_spec=after,
            )
            if organization.credits < cost:
                with translation.override(_project_language(project)):
                    credit_note = _(
                        "This change requires %(required)s credit(s), but your workspace currently has %(available)s. Add credits to continue."
                    ) % {"required": cost, "available": organization.credits}
                assistant.content = f"{result['message']}\n\n{credit_note}"
                assistant.status = "done"
                assistant.metadata = {"action": "payment_required", "credits": cost, "feature_id": str(feature.id)}
                assistant.save(update_fields=["content", "status", "metadata", "updated_at"])
                return {"status": "payment_required", "credits": cost}
            if cost:
                organization.credits -= cost
                organization.save(update_fields=["credits", "updated_at"])
                CreditTransaction.objects.create(
                    organization=organization,
                    project=locked_project,
                    feature_request=feature,
                    kind="usage",
                    amount=-cost,
                    balance_after=organization.credits,
                    description=result["feature_title"],
                )
            locked_project.app_spec = after
            locked_project.version += 1
            locked_project.status = "building"
            locked_project.save(update_fields=["app_spec", "version", "status", "updated_at"])
            project = locked_project

        deployment = Deployment.objects.create(project=project, feature_request=feature, environment="preview", status="building", version=project.version, url=project.preview_url)
        root, checksum = generate_preview(project)
        if settings.GITHUB_TOKEN:
            sync_project_repository(project, root)
        project.status = "preview"
        project.last_build_error = ""
        project.save(update_fields=["status", "last_build_error", "updated_at"])
        feature.status = "done"
        feature.save(update_fields=["status", "updated_at"])
        deployment.mark_success(project.preview_url, checksum)
        assistant.content = result["message"]
        assistant.status = "done"
        assistant.metadata = {
            "action": "preview_ready",
            "preview_url": project.preview_url,
            "version": project.version,
            "credits_used": cost,
            "feature_size": size,
            "feature_id": str(feature.id),
        }
        assistant.save(update_fields=["content", "status", "metadata", "updated_at"])
        return assistant.metadata
    except Exception as exc:
        with translation.override(_project_language(project)):
            assistant.content = _(
                "I could not complete this change safely. The previous version is untouched. The technical team can review the build log."
            )
        assistant.status = "failed"
        assistant.metadata = {"error": str(exc)[:1000]}
        assistant.save(update_fields=["content", "status", "metadata", "updated_at"])
        Project.objects.filter(pk=project.pk).update(status="error", last_build_error=str(exc)[:4000])
        raise


@shared_task(bind=True)
def publish_project_task(self, project_id):
    project = Project.objects.get(pk=project_id)
    deployment = Deployment.objects.create(project=project, environment="production", status="building", version=project.version, url=project.live_url)
    try:
        _root, checksum = publish_project(project)
        project.status = "live"
        project.published_at = timezone.now()
        project.save(update_fields=["status", "published_at", "updated_at"])
        deployment.mark_success(project.live_url, checksum)
        with translation.override(_project_language(project)):
            content = _(
                "The approved version is now live. You can keep chatting with me to prepare the next update without affecting production."
            )
        Message.objects.create(
            conversation=project.conversation,
            role="assistant",
            content=content,
            metadata={"action": "published", "live_url": project.live_url, "version": project.version},
        )
        return {"status": "success", "live_url": project.live_url}
    except Exception as exc:
        deployment.status = "failed"
        deployment.log = str(exc)
        deployment.save(update_fields=["status", "log", "updated_at"])
        raise
