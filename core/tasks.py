from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from .models import AuditEvent, CreditTransaction, Deployment, FeatureRequest, Message, Project, StoreSubmission
from .services.ai import propose_change
from .services.generator import generate_preview, publish_project
from .services.github import sync_project_repository
from .services.pricing import cost_for_size, estimate_size
from .services.provisioning import provision_project


def _project_language(project):
    return project.language if project.language in {"de", "en"} else "de"


def _set_message_progress(message, stage, percent):
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
    _set_message_progress(assistant, "analyzing", 12)
    try:
        history = list(user_message.conversation.messages.exclude(pk=assistant.pk).values("role", "content"))
        result = propose_change(project, user_message.content, history)
        _set_message_progress(assistant, "planning", 38)
        if result["action"] == "clarify":
            assistant.content = result["message"]
            assistant.status = "done"
            assistant.metadata = {"action": "clarify", "progress": {"stage": "ready", "percent": 100, "updated_at": timezone.now().isoformat()}}
            assistant.save(update_fields=["content", "status", "metadata", "updated_at"])
            return {"status": "clarify"}

        before = project.app_spec or {}
        after = result["spec"]
        size = estimate_size(before, after)
        cost = cost_for_size(size)
        _set_message_progress(assistant, "preparing", 48)

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
                assistant.metadata = {
                    "action": "payment_required",
                    "credits": cost,
                    "feature_id": str(feature.id),
                    "progress": {"stage": "ready", "percent": 100, "updated_at": timezone.now().isoformat()},
                }
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

        _set_message_progress(assistant, "building", 60)
        deployment = Deployment.objects.create(project=project, feature_request=feature, environment="preview", status="building", version=project.version, url=project.preview_url)
        root, checksum = generate_preview(project)
        _set_message_progress(assistant, "validating", 76)
        if settings.GITHUB_TOKEN:
            _set_message_progress(assistant, "syncing", 88)
            sync_project_repository(project, root)
        _set_message_progress(assistant, "finishing", 96)
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
            "progress": {"stage": "ready", "percent": 100, "updated_at": timezone.now().isoformat()},
        }
        assistant.save(update_fields=["content", "status", "metadata", "updated_at"])
        return assistant.metadata
    except Exception as exc:
        with translation.override(_project_language(project)):
            assistant.content = _(
                "I could not complete this change safely. The previous version is untouched. The technical team can review the build log."
            )
        assistant.status = "failed"
        assistant.metadata = {
            "error": str(exc)[:1000],
            "progress": {"stage": "failed", "percent": 100, "updated_at": timezone.now().isoformat()},
        }
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


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def notify_store_submission(self, submission_id):
    submission = StoreSubmission.objects.select_related("project__organization", "requested_by").get(pk=submission_id)
    project = submission.project
    team_email = getattr(settings, "STORE_REVIEW_EMAIL", settings.BILLING_CONTACT_EMAIL)
    admin_url = f"{settings.APP_PUBLIC_URL}/admin/core/storesubmission/{submission.id}/change/"
    request_url = f"{settings.APP_PUBLIC_URL}/projects/{project.id}/store-submissions/"
    requester = submission.requested_by.get_full_name() or submission.requested_by.email or submission.requested_by.username

    team_subject = f"[A+ Studio] Store publishing request · {project.name} · {submission.get_platform_display()}"
    team_body = (
        f"A new store publishing request needs review.\n\n"
        f"Project: {project.name}\n"
        f"Company: {project.organization.name}\n"
        f"Requested by: {requester} ({submission.requested_by.email})\n"
        f"Platform: {submission.get_platform_display()}\n"
        f"Current status: {submission.get_status_display()}\n"
        f"Project version: {project.version}\n"
        f"Live URL: {project.live_url or '-'}\n"
        f"Notes: {submission.notes or '-'}\n\n"
        f"Review in A+ admin: {admin_url}\n"
    )
    send_mail(team_subject, team_body, settings.DEFAULT_FROM_EMAIL, [team_email], fail_silently=False)

    if submission.requested_by.email:
        with translation.override(_project_language(project)):
            user_subject = _("Your A+ Studio store publishing request was received")
            user_body = _(
                "We received your store publishing request for %(project)s (%(platform)s).\n\n"
                "Current status: Requested\n"
                "A+ Solution will first review store eligibility and developer-account requirements. "
                "You can follow every status change in A+ Studio:\n%(url)s"
            ) % {"project": project.name, "platform": submission.get_platform_display(), "url": request_url}
        send_mail(user_subject, user_body, settings.DEFAULT_FROM_EMAIL, [submission.requested_by.email], fail_silently=False)

    AuditEvent.objects.create(
        organization=project.organization,
        user=submission.requested_by,
        project=project,
        action="store_submission_notification_sent",
        payload={"submission_id": str(submission.id), "team_email": team_email},
    )
    return {"status": "sent", "submission_id": str(submission.id)}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def notify_store_submission_status(self, submission_id):
    submission = StoreSubmission.objects.select_related("project", "requested_by").get(pk=submission_id)
    if not submission.requested_by.email:
        return {"status": "skipped"}
    project = submission.project
    request_url = f"{settings.APP_PUBLIC_URL}/projects/{project.id}/store-submissions/"
    with translation.override(_project_language(project)):
        subject = _("Your A+ Studio store publishing request was updated")
        body = _(
            "The status of your store publishing request for %(project)s (%(platform)s) is now: %(status)s.\n\n"
            "Follow the request here:\n%(url)s"
        ) % {
            "project": project.name,
            "platform": submission.get_platform_display(),
            "status": submission.get_status_display(),
            "url": request_url,
        }
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [submission.requested_by.email], fail_silently=False)
    return {"status": "sent", "submission_id": str(submission.id)}
