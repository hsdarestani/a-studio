import json
from functools import wraps

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import FeatureRequest, Membership, Organization, Project, StoreSubmission

User = get_user_model()
TOKEN_SALT = "a-studio-mobile-v1"
TOKEN_MAX_AGE = 60 * 60 * 24 * 7
MOBILE_READ_ONLY_ERROR = "mobile_existing_projects_only"


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
        credits=0,
    )
    Membership.objects.create(organization=organization, user=user, role="owner")
    return organization


def _project_for(user, pk):
    return (
        Project.objects.select_related("organization")
        .filter(pk=pk, organization__memberships__user=user)
        .first()
    )


def _mobile_project_status(status):
    """Expose neutral customer-project progress, not software lifecycle states."""
    return {
        "draft": "planning",
        "building": "active",
        "preview": "review",
        "live": "completed",
        "paused": "paused",
        "error": "attention",
    }.get(status, "active")


def _project_payload(project, *, detail=False):
    data = {
        "id": str(project.id),
        "name": project.name,
        "business_type": project.business_type,
        "language": project.language,
        "status": _mobile_project_status(project.status),
        "updated_at": project.updated_at.isoformat(),
    }
    if detail:
        data["description"] = project.description
        data["requests"] = [
            {
                "id": str(item.id),
                "title": item.title,
                "description": item.description,
                "status": item.status,
                "created_at": item.created_at.isoformat(),
            }
            for item in project.feature_requests.order_by("-created_at")[:20]
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
    """The iOS client is for invited/existing customer accounts only."""
    return JsonResponse({"ok": False, "error": MOBILE_READ_ONLY_ERROR}, status=403)


def _user_payload(user):
    organization = _organization_for(user)
    return {
        "id": user.pk,
        "email": user.email,
        "name": user.get_full_name() or user.email,
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
        },
    }


@mobile_endpoint("GET")
def config(request):
    base = settings.APP_PUBLIC_URL.rstrip("/")
    return JsonResponse({
        "ok": True,
        "app": "A+ Studio",
        "version": "1.0.0",
        "mode": "customer_project_companion",
        "capabilities": {
            "existing_account_access": True,
            "existing_project_status": True,
            "project_requests": True,
            "account_registration": False,
            "project_creation": False,
            "store_status": False,
            "code_execution": False,
            "external_app_preview": False,
            "mobile_publishing": False,
            "mobile_purchases": False,
        },
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
        "organization": {"name": organization.name},
        "projects": [_project_payload(project) for project in projects],
    })


@mobile_endpoint("POST", auth=True)
def project_create(request):
    """Project creation is intentionally unavailable in the iOS companion."""
    return JsonResponse({"ok": False, "error": MOBILE_READ_ONLY_ERROR}, status=403)


@mobile_endpoint("GET", auth=True)
def project_detail(request, pk):
    project = _project_for(request.mobile_user, pk)
    if not project:
        return JsonResponse({"ok": False, "error": "project_not_found"}, status=404)
    return JsonResponse({"ok": True, "project": _project_payload(project, detail=True)})


@mobile_endpoint("POST", auth=True)
def chat(request, pk):
    """Record a customer coordination request for human project-team review."""
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

    title = content.splitlines()[0].strip()[:220] or "Project request"
    item = FeatureRequest.objects.create(
        project=project,
        requested_by=request.mobile_user,
        title=title,
        description=content,
        size="custom",
        credits=0,
        status="proposed",
    )
    return JsonResponse(
        {
            "ok": True,
            "request": {
                "id": str(item.id),
                "title": item.title,
                "status": item.status,
                "created_at": item.created_at.isoformat(),
            },
        },
        status=201,
    )


@mobile_endpoint("GET", auth=True)
def message_status(request, pk, message_id):
    return JsonResponse({"ok": False, "error": "not_available"}, status=410)


@mobile_endpoint("POST", auth=True)
def publish(request, pk):
    return JsonResponse({"ok": False, "error": "not_available"}, status=404)


@mobile_endpoint("POST", auth=True)
def request_store_submission(request, pk):
    return JsonResponse({"ok": False, "error": "not_available"}, status=404)


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
