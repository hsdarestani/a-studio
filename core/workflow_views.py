from celery.result import AsyncResult
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from .models import Conversation, Message, Project, StoreSubmission
from .tasks import notify_store_submission, process_chat_message


def _project_for(user, pk):
    return get_object_or_404(
        Project.objects.select_related("organization"),
        pk=pk,
        organization__memberships__user=user,
    )


def _state(project):
    project.refresh_from_db()
    project.organization.refresh_from_db()
    latest = project.deployments.order_by("-created_at").first()
    return {
        "status": project.status,
        "version": project.version,
        "credits": project.organization.credits,
        "preview_url": project.preview_url,
        "live_url": project.live_url,
        "repo_url": project.repo_url,
        "repo_name": project.repo_name,
        "deployment": {
            "status": latest.status,
            "environment": latest.environment,
            "version": latest.version,
        } if latest else None,
    }


def _store_status_presentation(submission):
    status_map = {
        "requested": (10, _("Request received"), _("A+ Solution will review eligibility and the required developer accounts.")),
        "eligibility": (25, _("Eligibility review"), _("We are checking app content, store rules and release requirements.")),
        "accounts": (40, _("Waiting for developer accounts"), _("Developer-account access or setup information is required before packaging.")),
        "preparing": (58, _("Preparing store package"), _("A+ Solution is preparing the release package, metadata and store assets.")),
        "submitted": (72, _("Submitted to stores"), _("The package has been submitted and is waiting for store processing.")),
        "review": (86, _("In store review"), _("Apple and/or Google are reviewing the submission.")),
        "approved": (100, _("Approved"), _("The store submission has been approved.")),
        "rejected": (100, _("Needs attention"), _("The store rejected the submission. A+ Solution will review the reason and next action.")),
    }
    percent, label, next_step = status_map.get(submission.status, (0, submission.get_status_display(), ""))
    return {"submission": submission, "percent": percent, "label": label, "next_step": next_step}


@login_required
@require_POST
def chat_submit(request, pk):
    project = _project_for(request.user, pk)
    body = request.POST.get("message", "").strip()
    if not body:
        return JsonResponse({"error": _("A message is required.")}, status=400)
    if len(body) > 12000:
        return JsonResponse({"error": _("The message is too long.")}, status=400)

    conversation, _created = Conversation.objects.get_or_create(project=project)
    active = conversation.messages.filter(
        role="assistant",
        status__in=["queued", "working"],
    ).order_by("-created_at").first()
    if active:
        return JsonResponse(
            {
                "error": _("A build is already running. You can send the next request as soon as this build is ready."),
                "active_message_id": str(active.id),
            },
            status=409,
        )

    user_message = Message.objects.create(conversation=conversation, role="user", content=body)
    assistant = Message.objects.create(
        conversation=conversation,
        role="assistant",
        content=_("Request queued. A+ Builder is preparing the build."),
        status="queued",
        metadata={"progress": {"stage": "queued", "percent": 5}},
    )
    task = process_chat_message.delay(str(user_message.id), str(assistant.id), request.user.id)
    assistant.task_id = task.id
    assistant.save(update_fields=["task_id", "updated_at"])
    return JsonResponse({"task_id": task.id, "assistant_message_id": str(assistant.id)})


@login_required
@require_GET
def message_status(request, pk, message_id):
    project = _project_for(request.user, pk)
    message = get_object_or_404(Message, pk=message_id, conversation__project=project)
    task_state = AsyncResult(message.task_id).state if message.task_id else message.status.upper()
    state = _state(project)
    return JsonResponse(
        {
            "id": str(message.id),
            "status": message.status,
            "task_state": task_state,
            "content": message.content,
            "metadata": message.metadata,
            "credits": state["credits"],
            "project_status": state["status"],
            "project_version": state["version"],
            "preview_url": state["preview_url"],
            "repo_url": state["repo_url"],
            "deployment": state["deployment"],
        }
    )


@login_required
@require_POST
def request_store_submission(request, pk):
    project = _project_for(request.user, pk)
    platform = request.POST.get("platform", "both")
    if platform not in {"android", "ios", "both"}:
        platform = "both"

    active_statuses = ["requested", "eligibility", "accounts", "preparing", "submitted", "review"]
    existing = project.store_submissions.filter(
        platform=platform,
        status__in=active_statuses,
    ).order_by("-created_at").first()
    if existing:
        messages.info(
            request,
            _("You already have an active store publishing request for this platform. Its latest status is shown below."),
        )
        return redirect("store_submissions", pk=project.pk)

    submission = StoreSubmission.objects.create(
        project=project,
        requested_by=request.user,
        platform=platform,
        notes=request.POST.get("notes", "")[:4000],
        eligibility_report={
            "has_pwa": project.status in {"preview", "live"},
            "unique_content_review_required": True,
            "developer_accounts_required": True,
            "manual_a_plus_review": True,
        },
    )
    transaction.on_commit(lambda: notify_store_submission.delay(str(submission.id)))
    messages.success(
        request,
        _("Your store publhing request was created. You can follow its progress here, and A+ Solution has been notified."),
    )
    return redirect("store_submissions", pk=project.pk)


@login_required
@require_GET
def store_submissions(request, pk):
    project = _project_for(request.user, pk)
    submissions = project.store_submissions.select_related("requested_by").order_by("-created_at")
    return render(
        request,
        "store_submissions.html",
        {
            "project": project,
            "organization": project.organization,
            "submission_cards": [_store_status_presentation(item) for item in submissions],
        },
    )
