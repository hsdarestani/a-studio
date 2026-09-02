import json
import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from core.models import Project

from .models import AppRecord, AppUser
from .security import active_features, allow_attempt, authenticate_token, bearer_token, issue_token, user_payload


_COLLECTION = re.compile(r"^[a-z][a-z0-9_-]{0,79}$")
_SAFE_KEY = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
MAX_JSON_BYTES = 64 * 1024


def _project(slug):
    return get_object_or_404(Project, slug=slug, status__in={"preview", "live"})


def _origin_value(url):
    parsed = urlparse(str(url or ""))
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".lower()
    return ""


def _allowed_origins(project):
    from django.conf import settings

    values = {
        _origin_value(settings.APP_PUBLIC_URL),
        _origin_value(project.preview_url),
        _origin_value(project.live_url),
    }
    for host in [project.desired_domain, project.custom_domain]:
        if host:
            values.add(f"https://{host.strip().lower().strip('.')}")
    return {value for value in values if value}


def _cors(response, request, project):
    origin = request.headers.get("Origin", "").rstrip("/").lower()
    if origin and origin in _allowed_origins(project):
        response["Access-Control-Allow-Origin"] = origin
        response["Vary"] = "Origin"
    response["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response["Access-Control-Max-Age"] = "600"
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _reply(request, project, payload, status=200):
    return _cors(JsonResponse(payload, status=status), request, project)


def _body(request):
    if len(request.body or b"") > MAX_JSON_BYTES:
        raise ValueError("request_too_large")
    try:
        value = json.loads((request.body or b"{}").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_json") from exc
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


def _clean_value(value, depth=0):
    if depth > 6:
        raise ValueError("data_too_deep")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if abs(value) > 10**15:
            raise ValueError("number_out_of_range")
        return value
    if isinstance(value, str):
        return value[:4000]
    if isinstance(value, list):
        if len(value) > 100:
            raise ValueError("too_many_items")
        return [_clean_value(item, depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > 80:
            raise ValueError("too_many_fields")
        cleaned = {}
        for key, item in value.items():
            key = str(key)
            if not _SAFE_KEY.fullmatch(key):
                raise ValueError("invalid_field_name")
            cleaned[key] = _clean_value(item, depth + 1)
        return cleaned
    raise ValueError("unsupported_value")


def _require_feature(request, project, feature):
    if feature not in active_features(project):
        return _reply(request, project, {"error": "feature_not_enabled"}, status=404)
    return None


def _user_from_request(request, project):
    return authenticate_token(project, bearer_token(request))


def _record_payload(record):
    return {
        "id": str(record.id),
        "collection": record.collection,
        "data": record.data,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


@csrf_exempt
def config(request, slug):
    project = _project(slug)
    if request.method == "OPTIONS":
        return _reply(request, project, {}, status=204)
    if request.method != "GET":
        return _reply(request, project, {"error": "method_not_allowed"}, status=405)
    requested = [str(item) for item in (project.backend_features or [])]
    return _reply(
        request,
        project,
        {
            "api_version": 1,
            "project": project.slug,
            "features": active_features(project),
            "requested_features": requested,
            "auth": {"mode": "email_password"} if "auth" in active_features(project) else None,
            "database": {"scope": "owner", "max_records_per_page": 100} if "database" in active_features(project) else None,
        },
    )


@csrf_exempt
def signup(request, slug):
    project = _project(slug)
    if request.method == "OPTIONS":
        return _reply(request, project, {}, status=204)
    blocked = _require_feature(request, project, "auth")
    if blocked:
        return blocked
    if request.method != "POST":
        return _reply(request, project, {"error": "method_not_allowed"}, status=405)
    if not allow_attempt(project, request, "signup", limit=10, window_seconds=600):
        return _reply(request, project, {"error": "rate_limited"}, status=429)
    try:
        body = _body(request)
        email = str(body.get("email") or "").strip().lower()
        password = str(body.get("password") or "")
        display_name = str(body.get("display_name") or "").strip()[:160]
        validate_email(email)
        if len(password) < 8 or len(password) > 128:
            return _reply(request, project, {"error": "password_length"}, status=400)
    except ValidationError:
        return _reply(request, project, {"error": "invalid_email"}, status=400)
    except ValueError as exc:
        return _reply(request, project, {"error": str(exc)}, status=400)

    try:
        with transaction.atomic():
            user = AppUser(project=project, email=email, display_name=display_name)
            user.set_password(password)
            user.save()
    except IntegrityError:
        return _reply(request, project, {"error": "email_in_use"}, status=409)
    token = issue_token(user)
    return _reply(request, project, {"token": token, "user": user_payload(user)}, status=201)


@csrf_exempt
def login(request, slug):
    project = _project(slug)
    if request.method == "OPTIONS":
        return _reply(request, project, {}, status=204)
    blocked = _require_feature(request, project, "auth")
    if blocked:
        return blocked
    if request.method != "POST":
        return _reply(request, project, {"error": "method_not_allowed"}, status=405)
    if not allow_attempt(project, request, "login", limit=20, window_seconds=300):
        return _reply(request, project, {"error": "rate_limited"}, status=429)
    try:
        body = _body(request)
        email = str(body.get("email") or "").strip().lower()
        password = str(body.get("password") or "")
    except ValueError as exc:
        return _reply(request, project, {"error": str(exc)}, status=400)
    user = AppUser.objects.filter(project=project, email=email, active=True).first()
    if not user or not user.check_password(password):
        return _reply(request, project, {"error": "invalid_credentials"}, status=401)
    user.mark_login()
    return _reply(request, project, {"token": issue_token(user), "user": user_payload(user)})


@csrf_exempt
def me(request, slug):
    project = _project(slug)
    if request.method == "OPTIONS":
        return _reply(request, project, {}, status=204)
    blocked = _require_feature(request, project, "auth")
    if blocked:
        return blocked
    if request.method != "GET":
        return _reply(request, project, {"error": "method_not_allowed"}, status=405)
    user = _user_from_request(request, project)
    if not user:
        return _reply(request, project, {"error": "unauthorized"}, status=401)
    return _reply(request, project, {"user": user_payload(user)})


@csrf_exempt
def records(request, slug, collection):
    project = _project(slug)
    if request.method == "OPTIONS":
        return _reply(request, project, {}, status=204)
    blocked = _require_feature(request, project, "database")
    if blocked:
        return blocked
    if not _COLLECTION.fullmatch(collection or ""):
        return _reply(request, project, {"error": "invalid_collection"}, status=400)
    user = _user_from_request(request, project)
    if not user:
        return _reply(request, project, {"error": "unauthorized"}, status=401)

    if request.method == "GET":
        queryset = AppRecord.objects.filter(project=project, owner=user, collection=collection)[:100]
        return _reply(request, project, {"records": [_record_payload(record) for record in queryset]})
    if request.method == "POST":
        try:
            body = _body(request)
            data = _clean_value(body.get("data", {}))
            if not isinstance(data, dict):
                raise ValueError("data_object_required")
        except ValueError as exc:
            return _reply(request, project, {"error": str(exc)}, status=400)
        record = AppRecord.objects.create(project=project, owner=user, collection=collection, data=data)
        return _reply(request, project, {"record": _record_payload(record)}, status=201)
    return _reply(request, project, {"error": "method_not_allowed"}, status=405)


@csrf_exempt
def record_detail(request, slug, collection, record_id):
    project = _project(slug)
    if request.method == "OPTIONS":
        return _reply(request, project, {}, status=204)
    blocked = _require_feature(request, project, "database")
    if blocked:
        return blocked
    if not _COLLECTION.fullmatch(collection or ""):
        return _reply(request, project, {"error": "invalid_collection"}, status=400)
    user = _user_from_request(request, project)
    if not user:
        return _reply(request, project, {"error": "unauthorized"}, status=401)
    record = get_object_or_404(AppRecord, pk=record_id, project=project, owner=user, collection=collection)

    if request.method == "GET":
        return _reply(request, project, {"record": _record_payload(record)})
    if request.method == "PATCH":
        try:
            body = _body(request)
            data = _clean_value(body.get("data", {}))
            if not isinstance(data, dict):
                raise ValueError("data_object_required")
        except ValueError as exc:
            return _reply(request, project, {"error": str(exc)}, status=400)
        record.data = data
        record.save(update_fields=["data", "updated_at"])
        return _reply(request, project, {"record": _record_payload(record)})
    if request.method == "DELETE":
        record.delete()
        return _reply(request, project, {"deleted": True})
    return _reply(request, project, {"error": "method_not_allowed"}, status=405)
