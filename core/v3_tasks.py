from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from .models import CreditTransaction, Deployment, FeatureRequest, Message, Project
from .services.code_agent import apply_code_change, propose_code_change
from .services.code_workspace import list_files
from .services.github import sync_project_repository
from .services.pricing import cost_for_size


def _project_language(project):
    return project.language if project.language in {"de", "en"} else "de"


def _set_progress(message, stage, percent):
    metadata = dict(message.metadata or {})
    metadata["progress"] = {
        "stage": stage,
        "percent": max(0, min(100, int(percent))),
        "updated_at": timezone.now().isoformat(),
    }
    message.metadata = metadata
    if message.status not in {"done", "failed"}:
        message.status = "working"
    message.save(update_fields=["metadata", "status", "updated_at"])


def _size_for_proposal(proposal):
    changed = len(proposal.get("files") or []) + len(proposal.get("deleted_files") or [])
    if changed <= 0:
        return "micro"
    if changed <= 2:
        return "small"
    if changed <= 6:
        return "standard"
    return "advanced"


@shared_task(bind=True)
def process_code_chat_message(self, user_message_id, assistant_message_id, user_id):
    user_message = Message.objects.select_related("conversation__project__organization").get(pk=user_message_id)
    assistant = Message.objects.get(pk=assistant_message_id)
    project = user_message.conversation.project
    _set_progress(assistant, "reading_code", 12)
    try:
        history = list(
            user_message.conversation.messages.exclude(pk=assistant.pk)
            .order_by("-created_at")[:16]
            .values("role", "content")
        )
        history.reverse()
        proposal = propose_code_change(project, user_message.content, history)
        _set_progress(assistant, "planning_patch", 34)
        if proposal["action"] == "clarify":
            assistant.content = proposal["message"]
            assistant.status = "done"
            assistant.metadata = {
                "action": "clarify",
                "builder_mode": "code_agent",
                "progress": {"stage": "ready", "percent": 100, "updated_at": timezone.now().isoformat()},
            }
            assistant.save(update_fields=["content", "status", "metadata", "updated_at"])
            return {"status": "clarify"}

        size = _size_for_proposal(proposal)
        cost = cost_for_size(size)
        before_files = list_files(project)
        _set_progress(assistant, "reserving_revision", 46)
        with transaction.atomic():
            locked = Project.objects.select_for_update().select_related("organization").get(pk=project.pk)
            organization = locked.organization
            feature = FeatureRequest.objects.create(
                project=locked,
                requested_by_id=user_id,
                title=proposal["feature_title"],
                description=proposal["feature_description"],
                size=size,
                credits=cost,
                status="building" if organization.credits >= cost else "proposed",
                before_spec={"mode": "code_workspace", "version": locked.version, "files": before_files},
                after_spec={
                    "mode": "code_workspace",
                    "changed_files": [item.get("path") for item in proposal.get("files") or []],
                    "deleted_files": proposal.get("deleted_files") or [],
                },
            )
            if organization.credits < cost:
                with translation.override(_project_language(project)):
                    note = _(
                        "This code change requires %(required)s credit(s), but your workspace currently has %(available)s. Add credits to continue."
                    ) % {"required": cost, "available": organization.credits}
                assistant.content = f"{proposal['message']}\n\n{note}"
                assistant.status = "done"
                assistant.metadata = {
                    "action": "payment_required",
                    "credits": cost,
                    "feature_id": str(feature.id),
                    "builder_mode": "code_agent",
                    "progress": {"stage": "ready", "percent": 100, "updated_at": timezone.now().isoformat()},
                }
                assistant.save(update_fields=["content", "status", "metadata", "updated_at"])
                return {"status": "payment_required", "credits": cost}
            if cost:
                organization.credits -= cost
                organization.save(update_fields=["credits", "updated_at"])
                CreditTransaction.objects.create(
                    organization=organization,
                    project=locked,
                    feature_request=feature,
                    kind="usage",
                    amount=-cost,
                    balance_after=organization.credits,
                    description=proposal["feature_title"],
                )
            locked.status = "building"
            locked.version += 1
            locked.save(update_fields=["status", "version", "updated_at"])
            project = locked

        deployment = Deployment.objects.create(
            project=project,
            feature_request=feature,
            environment="preview",
            status="building",
            version=project.version,
            url=project.preview_url,
        )
        _set_progress(assistant, "writing_code", 58)
        result = apply_code_change(project, proposal)
        _set_progress(assistant, "validating_preview", 76)
        if settings.GITHUB_TOKEN:
            _set_progress(assistant, "syncing_repository", 88)
            sync_project_repository(project, result["root"])
        project.status = "preview"
        project.last_build_error = ""
        project.save(update_fields=["status", "last_build_error", "updated_at"])
        feature.status = "done"
        feature.after_spec = {
            **(feature.after_spec or {}),
            "version": project.version,
            "files": list_files(project),
            "snapshot": result.get("snapshot", ""),
        }
        feature.save(update_fields=["status", "after_spec", "updated_at"])
        deployment.mark_success(project.preview_url, result["checksum"])
        assistant.content = proposal["message"] or _("The code change is ready in preview.")
        assistant.status = "done"
        assistant.metadata = {
            "action": "code_preview_ready",
            "preview_url": project.preview_url,
            "version": project.version,
            "credits_used": cost,
            "feature_size": size,
            "feature_id": str(feature.id),
            "changed_files": result.get("files_changed", []),
            "deleted_files": result.get("files_deleted", []),
            "builder_mode": "code_agent",
            "progress": {"stage": "ready", "percent": 100, "updated_at": timezone.now().isoformat()},
        }
        assistant.save(update_fields=["content", "status", "metadata", "updated_at"])
        return assistant.metadata
    except Exception as exc:
        with translation.override(_project_language(project)):
            assistant.content = _(
                "I could not complete this code change safely. The previous revision is still available and production was not changed."
            )
        assistant.status = "failed"
        assistant.metadata = {
            "error": str(exc)[:1000],
            "builder_mode": "code_agent",
            "progress": {"stage": "failed", "percent": 100, "updated_at": timezone.now().isoformat()},
        }
        assistant.save(update_fields=["content", "status", "metadata", "updated_at"])
        Project.objects.filter(pk=project.pk).update(status="error", last_build_error=str(exc)[:4000])
        raise
