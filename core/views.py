import json
from pathlib import Path
import shutil
from celery.result import AsyncResult
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from .forms import ProjectCreateForm, SignUpForm
from .models import Conversation, CreditTransaction, Membership, Message, Organization, Project, StoreSubmission
from .services.pricing import PLANS
from .tasks import process_chat_message, provision_initial_project, publish_project_task


def _organization_for(user):
    membership = Membership.objects.select_related("organization").filter(user=user, organization__active=True).first()
    if not membership:
        organization = Organization.objects.create(
            name=_('%(name)s workspace') % {"name": user.get_full_name() or user.username},
            owner=user,
            billing_email=user.email,
        )
        Membership.objects.create(organization=organization, user=user, role="owner")
        return organization
    return membership.organization


def _project_for(user, pk):
    return get_object_or_404(Project.objects.select_related("organization"), pk=pk, organization__memberships__user=user)


def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None)

if request.method == "POST" and form.is_valid():
    with transaction.atomic():
        user = form.save()
        organization = Organization.objects.create(
            name=form.cleaned_data["company_name"],
            owner=user,
            billing_email=user.email,
            credits=20,
        )
        Membership.objects.create(organization=organization, user=user, role="owner")
        CreditTransaction.objects.create(
            organization=organization,
            kind="grant",
            amount=20,
            balance_after=20,
            description=_("Welcome credits"),
        )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("project_create")
    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard(request):
    organization = _organization_for(request.user)
    projects = organization.projects.order_by("-updated_at")
    return render(request, "dashboard.html", {"organization": organization, "projects": projects})


@login_required
def project_create(request):
    organization = _organization_for(request.user)
    form = ProjectCreateForm(request.POST or None, initial={"language": request.LANGUAGE_CODE if request.LANGUAGE_CODE in {"de", "en"} else "de"})
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.organization = organization
        project.created_by = request.user
        project.save()
        Conversation.objects.create(project=project)
        provision_initial_project.delay(str(project.id))
        messages.success(request, _("Your project is being prepared. The first preview will appear in the conversation."))
        return redirect("project_detail", pk=project.id)
    return render(request, "project_create.html", {"form": form, "organization": organization})


@login_required
def project_detail(request, pk):
    project = _project_for(request.user, pk)
    conversation, _created = Conversation.objects.get_or_create(project=project)
    chat_messages = conversation.messages.order_by("created_at")
    return render(request, "project_detail.html", {
        "project": project,
        "conversation": conversation,
        "chat_messages": chat_messages,
        "organization": project.organization,
        "deployments": project.deployments.order_by("-created_at")[:8],
    })


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
    user_message = Message.objects.create(conversation=conversation, role="user", content=body)
    assistant = Message.objects.create(conversation=conversation, role="assistant", content=_("Working on your request…"), status="queued")
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
    return JsonResponse({
        "id": str(message.id),
        "status": message.status,
        "task_state": task_state,
        "content": message.content,
        "metadata": message.metadata,
        "credits": project.organization.credits,
        "project_status": Project.objects.get(pk=project.pk).status,
    })


@login_required
@require_POST
def publish_project(request, pk):
    project = _project_for(request.user, pk)
    if project.status not in {"preview", "live"}:
        messages.error(request, _("A successful preview build is required before publishing."))
        return redirect("project_detail", pk=project.pk)
    publish_project_task.delay(str(project.id))
    messages.success(request, _("Publishing has started. Production remains untouched until the approved files are copied successfully."))
    return redirect("project_detail", pk=project.pk)


@login_required
@require_POST
def request_store_submission(request, pk):
    project = _project_for(request.user, pk)
    platform = request.POST.get("platform", "both")
    if platform not in {"android", "ios", "both"}:
        platform = "both"
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
    messages.success(
        request,
        _("A store publishing request was created for %(platform)s. A+ Solution will review eligibility and developer-account requirements.")
        % {"platform": submission.get_platform_display()},
    )
    return redirect("project_detail", pk=project.pk)


@login_required
def billing(request):
    organization = _organization_for(request.user)
    return render(request, "billing.html", {
        "organization": organization,
        "plans": PLANS,
        "billing_contact_email": settings.BILLING_CONTACT_EMAIL,
    })


@login_required
def export_spec(request, pk):
    project = _project_for(request.user, pk)
    response = HttpResponse(json.dumps(project.app_spec, ensure_ascii=False, indent=2), content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="{project.slug}-app-spec.json"'
    return response


@login_required
def download_build(request, pk):
    project = _project_for(request.user, pk)
    source = Path(settings.APP_DATA_ROOT) / "preview" / project.slug
    if not source.exists():
        raise Http404
    archive = shutil.make_archive(f"/tmp/{project.slug}-pwa", "zip", source)
    return FileResponse(open(archive, "rb"), as_attachment=True, filename=f"{project.slug}-pwa.zip")


@require_GET
def tls_allow(request):
    domain = request.GET.get("domain", "").lower().strip(".")
    allowed = bool(domain and Project.objects.filter(desired_domain=domain, status="live").exists())
    if not allowed:
        allowed = bool(domain and Project.objects.filter(custom_domain=domain, status="live").exists())
    return HttpResponse("allowed" if allowed else "denied", status=200 if allowed else 403)


@require_GET
def health(request):
    return JsonResponse({"status": "ok", "service": "a-studio"})
