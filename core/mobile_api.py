import json
from functools import wraps

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .forms import ProjectCreateForm
from .models import (
    Conversation,
    CreditTransaction,
    FeatureRequest,
    Membership,
    Message,
    Organization,
    Project,
    StoreSubmission,
)
from .tasks import process_chat_message, provision_initial_project, publish_project_task

User = get_user_model()
TOKEN_SALT = "a-studio-mobile-v1"
TOKEN_MAX_AGE = 60 * 60 * 24 * 7


def _json_body(request):
    if not request.body:
        return {}
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("invalid_json")
    if not isinstance(payload, dict):
        raise ValueError("invalid_json")
    return payload


def _issue_token(user):
    return signing.dumps(
        {"uid": user.pk, "auth": user.get_session_auth_hash()},
        salt=TOKEN_SALT,
        compress=True,
    )


def _token_user(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header[7:].strip()
    if not token:
        return None
    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
        user = User.objects.filter(pk=payload.get("uid"), is_active=True).first()
    except (signing.BadSignature, signing.SignatureExpired, TypeError, ValueError):
        return None
    if not user or payload.get("auth") != user.get_session_auth_hash():
        return None
    return user


def mobile_endpoint(*methods, auth=False):
    allowed_methods = {method.upper() for method in methods}

    def decorator(view):
        @csrf_exempt
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method == "OPTIONS":
                response = HttpResponse(status=204)
            elif request.method not in allowed_methods:
                response = JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)
            else:
                if auth:
                    user = _token_user(request)
                    if not user:
                        response = JsonResponse(
                            {"ok": False, "error": "authentication_required"},
                            status=401,
                        )
                    else:
                        request.mobile_user = user
                        response = view(request, *args, **kwargs)
                else:
                    response = view(request, *args, **kwargs)

            origin = request.headers.get("Origin", "")
            if origin in {"capacitor://localhost", "http://localhost", "https://localhost"}:
                response["Access-Control-Allow-Origin"] = origin
                response["Vary"] = "Origin"
                response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
                response["Access-Control-Allow-Methods"] = ", ".join(sorted(allowed_methods | {"OPTIONS"}))
                response["Access-Control-Max-Age"] = "86400"
            return response

        return wrapped

    return decorator


def _organization_for(user):
    membership = (
        Membership.objects.select_related("organization")
        .filter(user=user, organization__active=True)
        .first()
    )
    if membership:
        return membership.organization
    organization = Organization.objects.create(
        name=f"{user.get_full_name() or user.email or user.username} workspace",
        owner=user,
        billing_email=user.email,
    )
    Membership.objects.create(organization=organization, user=user, role="owner")
    return organization


def _project_for(user, pk):
    return (
        Project.objects.select_related("organization")
        .filter(pk=pk, organization__memberships__user=user)
        .first()
    )


def _project_payload(project, *, detail=False):
    latest = project.deployments.order_by("-created_at").first()
    data = {
        "id": str(project.id),
        "name": project.name,
        "business_type": project.business_type,
        "language": project.language,
        "status": project.status,
        "version": project.version,
        "preview_url": project.preview_url,
        "live_url": project.live_url,
        "repo_url": project.repo_url,
        "last_build_error": project.last_build_error,
        "updated_at": project.updated_at.isoformat(),
        "deployment": {
            "status": latest.status,
            "environment": latest.environment,
            "version": latest.version,
            "url": latest.url,
        } if latest else None,
    }
    if detail:
        data["description"] = project.description
        conversation = Conversation.objects.filter(project=project).first()
        messages = conversation.messages.order_by("-created_at")[:40] if conversation else []
        data["messages"] = [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "status": message.status,
                "created_at": message.created_at.isoformat(),
            }
            for message in reversed(list(messages))
        ]
        data["store_submissions"] = [
            {
                "id": str(item.id),
                "platform": item.platform,
                "status": item.status,
                "created_at": item.created_at.isoformat(),
            }
            for item in project.store_submissions.order_by("-created_at")[:8]
        ]
    return data


@mobile_endpoint("POST")
def login(request):
    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    email = str(payload.get("email") or payload.get("username") or "").lower().strip()
    password = str(payload.get("password") or "")
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if not user or not user.check_password(password):
        return JsonResponse({"ok": False, "error": "invalid_credentials"}, status=401)
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    return JsonResponse({"ok": True, "token": _issue_token(user), "user": _user_payload(user)})


@mobile_endpoint("POST")
def signup(request):
    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    email = str(payload.get("email") or "").lower().strip()
    password = str(payload.get("password") or "")
    full_name = str(payload.get("full_name") or "").strip()
    company_name = str(payload.get("company_name") or "").strip()

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"ok": False, "error": "valid_email_required"}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"ok": False, "error": "email_exists"}, status=409)
    if len(full_name) < 2 or len(company_name) < 2:
        return JsonResponse({"ok": False, "error": "profile_fields_required"}, status=400)

    provisional = User(username=email, email=email)
    parts = full_name.split(" ", 1)
    provisional.first_name = parts[0]
    provisional.last_name = parts[1] if len(parts) > 1 else ""
    try:
        validate_password(password, user=provisional)
    except ValidationError as exc:
        return JsonResponse(
            {"ok": False, "error": "weak_password", "details": list(exc.messages)},
            status=400,
        )

    with transaction.atomic():
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=provisional.first_name,
            last_name=provisional.last_name,
        )
        organization = Organization.objects.create(
            name=company_name,
            owner=user,
            billing_email=email,
            credits=20,
        )
        Membership.objects.create(organization=organization, user=user, role="owner")
        CreditTransaction.objects.create(
            organization=organization,
            kind="grant",
            amount=20,
            balance_after=20,
            description="Welcome credits",
        )
    return JsonResponse(
        {"ok": True, "token": _issue_token(user), "user": _user_payload(user)},
        status=201,
    )


def _user_payload(user):
    organization = _organization_for(user)
    return {
        "id": user.pk,
        "email": user.email,
        "name": user.get_full_name() or user.email,
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "plan": organization.plan,
            "credits": organization.credits,
        },
    }


@mobile_endpoint("GET")
def config(request):
    base = settings.APP_PUBLIC_URL.rstrip("/")
    return JsonResponse({
        "ok": True,
        "app": "A+ Studio",
        "version": "1.0.0",
        "legal": {
            "privacy": f"{base}/privacy/",
            "terms": f"{base}/terms/",
            "support": f"{base}/support/",
            "account_deletion": f"{base}/account-deletion/",
        },
    })


@mobile_endpoint("GET", auth=True)
def me(request):
    return JsonResponse({"ok": True, "user": _user_payload(request.mobile_user)})


@mobile_endpoint("GET", auth=True)
def dashboard(request):
    organization = _organization_for(request.mobile_user)
    projects = organization.projects.order_by("-updated_at")
    return JsonResponse({
        "ok": True,
        "organization": {
            "name": organization.name,
            "plan": organization.plan,
            "credits": organization.credits,
        },
        "projects": [_project_payload(project) for project in projects],
    })


@mobile_endpoint("POST", auth=True)
def project_create(request):
    organization = _organization_for(request.mobile_user)
    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    form = ProjectCreateForm(payload)
    if not form.is_valid():
        return JsonResponse(
            {"ok": False, "error": "invalid_project", "fields": form.errors.get_json_data()},
            status=400,
        )
    project = form.save(commit=False)
    project.organization = organization
    project.created_by = request.mobile_user
    project.save()
    Conversation.objects.create(project=project)
    provision_initial_project.delay(str(project.id))
    return JsonResponse({"ok": True, "project": _project_payload(project, detail=True)}, status=201)


@mobile_endpoint("GET", auth=True)
def project_detail(request, pk):
    project = _project_for(request.mobile_user, pk)
    if not project:
        return JsonResponse({"ok": False, "error": "project_not_found"}, status=404)
    return JsonResponse({"ok": True, "project": _project_payload(project, detail=True)})


@mobile_endpoint("POST", auth=True)
def chat(request, pk):
    project = _project_for(request.mobile_user, pk)
    if not project:
        return JsonResponse({"ok": False, "error": "project_not_found"}, status=404)
    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    content = str(payload.get("message") or "").strip()
    if not content:
        return JsonResponse({"ok": False, "error": "message_required"}, status=400)
    if len(content) > 12000:
        return JsonResponse({"ok": False, "error": "message_too_long"}, status=400)
    conversation, _ = Conversation.objects.get_or_create(project=project)
    user_message = Message.objects.create(conversation=conversation, role="user", content=content)
    assistant = Message.objects.create(
        conversation=conversation,
        role="assistant",
        content="Working on your request…",
        status="queued",
    )
    task = process_chat_message.delay(str(user_message.id), str(assistant.id), request.mobile_user.id)
    assistant.task_id = task.id
    assistant.save(update_fields=["task_id", "updated_at"])
    return JsonResponse(
        {"ok": True, "assistant_message_id": str(assistant.id), "task_id": task.id},
        status=202,
    )


@mobile_endpoint("GET", auth=True)
def message_status(request, pk, message_id):
    project = _project_for(request.mobile_user, pk)
    if not project:
        return JsonResponse({"ok": False, "error": "project_not_found"}, status=404)
    message = Message.objects.filter(pk=message_id, conversation__project=project).first()
    if not message:
        return JsonResponse({"ok": False, "error": "message_not_found"}, status=404)
    project.refresh_from_db()
    return JsonResponse({
        "ok": True,
        "message": {
            "id": str(message.id),
            "status": message.status,
            "content": message.content,
            "metadata": message.metadata,
        },
        "project": _project_payload(project),
    })


@mobile_endpoint("POST", auth=True)
def publish(request, pk):
    project = _project_for(request.mobile_user, pk)
    if not project:
        return JsonResponse({"ok": False, "error": "project_not_found"}, status=404)
    if project.status not in {"preview", "live"}:
        return JsonResponse({"ok": False, "error": "preview_required"}, status=409)
    publish_project_task.delay(str(project.id))
    return JsonResponse({"ok": True, "status": "publishing"}, status=202)


@mobile_endpoint("POST", auth=True)
def request_store_submission(request, pk):
    project = _project_for(request.mobile_user, pk)
    if not project:
        return JsonResponse({"ok": False, "error": "project_not_found"}, status=404)
    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    platform = str(payload.get("platform") or "both").lower()
    if platform not in {"android", "ios", "both"}:
        return JsonResponse({"ok": False, "error": "invalid_platform"}, status=400)
    submission = StoreSubmission.objects.create(
        project=project,
        requested_by=request.mobile_user,
        platform=platform,
        notes=str(payload.get("notes") or "")[:4000],
        eligibility_report={
            "has_pwa": project.status in {"preview", "live"},
            "unique_content_review_required": True,
            "developer_accounts_required": True,
            "manual_a_plus_review": True,
        },
    )
    return JsonResponse(
        {
            "ok": True,
            "submission": {
                "id": str(submission.id),
                "platform": submission.platform,
                "status": submission.status,
            },
        },
        status=201,
    )


def _delete_user_data(user):
    # A workspace with other members is company data, not disposable personal
    # data. Transfer ownership before removing the departing account. A
    # single-member workspace is removed together with its projects.
    for organization in list(Organization.objects.filter(owner=user)):
        successor_membership = (
            organization.memberships.select_related("user")
            .exclude(user=user)
            .order_by("role", "created_at")
            .first()
        )
        if successor_membership:
            successor = successor_membership.user
            organization.owner = successor
            if organization.billing_email.lower() == (user.email or "").lower():
                organization.billing_email = successor.email
            organization.save(update_fields=["owner", "billing_email", "updated_at"])
        else:
            organization.delete()

    # In surviving shared workspaces, preserve company-owned records while
    # removing the departing user's identifying foreign keys.
    for project in Project.objects.filter(created_by=user).select_related("organization__owner"):
        project.created_by = project.organization.owner
        project.save(update_fields=["created_by", "updated_at"])

    for item in FeatureRequest.objects.filter(requested_by=user).select_related("project__organization__owner"):
        item.requested_by = item.project.organization.owner
        item.save(update_fields=["requested_by", "updated_at"])

    for item in StoreSubmission.objects.filter(requested_by=user).select_related("project__organization__owner"):
        item.requested_by = item.project.organization.owner
        item.save(update_fields=["requested_by", "updated_at"])

    user.delete()


@mobile_endpoint("POST", auth=True)
def account_delete(request):
    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    if str(payload.get("confirmation") or "").upper() != "DELETE":
        return JsonResponse({"ok": False, "error": "confirmation_required"}, status=400)
    with transaction.atomic():
        _delete_user_data(request.mobile_user)
    return JsonResponse({"ok": True, "deleted": True})
