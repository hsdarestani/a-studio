import hashlib
import time

import jwt
import redis
from django.conf import settings
from django.utils import timezone

from .models import AppUser


SUPPORTED_FEATURES = ("auth", "database")


def active_features(project):
    requested = [str(item) for item in (project.backend_features or [])]
    active = [item for item in SUPPORTED_FEATURES if item in requested]
    if "database" in active and "auth" not in active:
        active.insert(0, "auth")
    return active


def _signing_key():
    return getattr(settings, "MANAGED_BACKEND_SIGNING_KEY", "") or settings.SECRET_KEY


def issue_token(user, ttl_seconds=None):
    now = int(time.time())
    ttl = int(ttl_seconds or getattr(settings, "MANAGED_BACKEND_TOKEN_TTL", 604800))
    payload = {
        "iss": "a-plus-studio",
        "aud": "a-plus-managed-app",
        "typ": "app_user",
        "sub": str(user.id),
        "pid": str(user.project_id),
        "iat": now,
        "nbf": now - 5,
        "exp": now + max(300, min(ttl, 2592000)),
    }
    return jwt.encode(payload, _signing_key(), algorithm="HS256")


def authenticate_token(project, token):
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            _signing_key(),
            algorithms=["HS256"],
            audience="a-plus-managed-app",
            issuer="a-plus-studio",
            options={"require": ["exp", "iat", "sub", "pid", "typ"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "app_user" or str(payload.get("pid")) != str(project.id):
        return None
    return AppUser.objects.filter(pk=payload.get("sub"), project=project, active=True).first()


def bearer_token(request):
    header = request.headers.get("Authorization", "").strip()
    if not header.lower().startswith("bearer "):
        return ""
    return header.split(" ", 1)[1].strip()


def client_fingerprint(request):
    forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
    ip = forwarded or request.META.get("REMOTE_ADDR", "unknown")
    agent = request.headers.get("User-Agent", "")[:200]
    return hashlib.sha256(f"{ip}|{agent}".encode("utf-8")).hexdigest()[:24]


def allow_attempt(project, request, bucket, limit=20, window_seconds=300):
    """Best-effort rate limit. Fails open when Redis is unavailable."""
    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=1, socket_timeout=1)
        window = int(time.time()) // max(1, int(window_seconds))
        key = f"astudio:managed:{project.id}:{bucket}:{client_fingerprint(request)}:{window}"
        pipeline = client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, int(window_seconds) + 30)
        count, _ = pipeline.execute()
        return int(count) <= int(limit)
    except Exception:
        return True


def user_payload(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "created_at": user.created_at.isoformat() if user.created_at else timezone.now().isoformat(),
    }
