import hashlib
import hmac
import json
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.utils import timezone

from ..models import AuditEvent, Deployment, Message, SandboxRun


class SandboxUnavailable(RuntimeError):
    pass


def sandbox_ready():
    return bool(
        getattr(settings, "CODE_AGENT_ENABLED", False)
        and getattr(settings, "CODE_SANDBOX_ENDPOINT", "")
        and getattr(settings, "CODE_SANDBOX_SHARED_SECRET", "")
    )


def _signature(raw):
    secret = getattr(settings, "CODE_SANDBOX_SHARED_SECRET", "").encode("utf-8")
    return "sha256=" + hmac.new(secret, raw, hashlib.sha256).hexdigest()


def verify_signature(raw, supplied):
    if not sandbox_ready() or not supplied:
        return False
    return hmac.compare_digest(_signature(raw), supplied.strip())


def _safe_result_url(value):
    value = str(value or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return value[:1000]


def dispatch_code_agent(project, requested_by, instructions, deployment_id=None):
    run = SandboxRun.objects.create(
        project=project,
        requested_by=requested_by,
        kind="build",
        status="queued",
        runtime=getattr(settings, "CODE_SANDBOX_RUNTIME", "node20"),
        image=getattr(settings, "CODE_SANDBOX_IMAGE", ""),
        network_policy="restricted",
        cpu_limit_millis=int(getattr(settings, "CODE_SANDBOX_CPU_MILLIS", 1000)),
        memory_limit_mb=int(getattr(settings, "CODE_SANDBOX_MEMORY_MB", 768)),
        timeout_seconds=int(getattr(settings, "CODE_SANDBOX_TIMEOUT_SECONDS", 300)),
    )
    if not sandbox_ready():
        run.status = "blocked"
        run.log = "Code Agent is disabled until the isolated sandbox endpoint and shared secret are configured."
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "log", "finished_at", "updated_at"])
        raise SandboxUnavailable(run.log)

    endpoint = getattr(settings, "CODE_SANDBOX_ENDPOINT", "").rstrip("/") + "/v1/runs"
    payload = {
        "run_id": str(run.id),
        "callback_url": f"{settings.APP_PUBLIC_URL}/api/sandbox/runs/{run.id}/callback/",
        "project": {
            "id": str(project.id),
            "name": project.name,
            "slug": project.slug,
            "business_type": project.business_type,
            "description": project.description,
            "language": project.language,
            "source_type": project.source_type,
            "source_url": project.source_url,
            "source_metadata": project.source_metadata,
            "backend_features": project.backend_features,
            "repo_url": project.repo_url,
            "version": project.version,
        },
        "job": {
            "kind": "initial_build",
            "instructions": instructions[:40_000],
            "runtime": run.runtime,
            "image": run.image,
            "network_policy": run.network_policy,
            "limits": {
                "cpu_millis": run.cpu_limit_millis,
                "memory_mb": run.memory_limit_mb,
                "timeout_seconds": run.timeout_seconds,
            },
        },
        "deployment_id": str(deployment_id) if deployment_id else "",
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    run.status = "starting"
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at", "updated_at"])
    try:
        response = requests.post(
            endpoint,
            data=raw,
            headers={
                "Content-Type": "application/json",
                "X-AStudio-Signature": _signature(raw),
                "User-Agent": "APlus-Studio-CodeAgent/2",
            },
            timeout=(5, 20),
        )
        response.raise_for_status()
        acknowledgement = response.json() if response.content else {}
        run.status = "running"
        run.result = {"ack": acknowledgement}
        run.save(update_fields=["status", "result", "updated_at"])
        AuditEvent.objects.create(
            organization=project.organization,
            user=requested_by,
            project=project,
            action="code_agent_dispatched",
            payload={"sandbox_run_id": str(run.id), "deployment_id": str(deployment_id or "")},
        )
        return run
    except Exception as exc:
        run.status = "failed"
        run.log = str(exc)[:4000]
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "log", "finished_at", "updated_at"])
        raise


def apply_sandbox_callback(run, payload):
    status = str(payload.get("status") or "").lower()
    if status not in {"running", "success", "failed"}:
        raise ValueError("Unsupported sandbox status")
    if run.status in {"success", "failed", "blocked"}:
        return run

    project = run.project
    if status == "running":
        run.status = "running"
        run.log = str(payload.get("log") or run.log)[-20_000:]
        run.save(update_fields=["status", "log", "updated_at"])
        return run

    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    run.result = result
    run.log = str(payload.get("log") or "")[-20_000:]
    run.finished_at = timezone.now()

    deployment_id = payload.get("deployment_id") or result.get("deployment_id")
    deployment = None
    if deployment_id:
        deployment = Deployment.objects.filter(pk=deployment_id, project=project).first()
    if deployment is None:
        deployment = project.deployments.filter(environment="preview", status="building").order_by("-created_at").first()

    if status == "failed":
        run.status = "failed"
        run.save(update_fields=["status", "result", "log", "finished_at", "updated_at"])
        project.status = "error"
        project.last_build_error = run.log or str(result.get("error") or "Code Agent build failed")
        project.save(update_fields=["status", "last_build_error", "updated_at"])
        if deployment:
            deployment.status = "failed"
            deployment.log = project.last_build_error[:4000]
            deployment.save(update_fields=["status", "log", "updated_at"])
        Message.objects.create(
            conversation=project.conversation,
            role="assistant",
            status="failed",
            content="The isolated Code Agent build failed. Production was not changed.",
            metadata={"sandbox_run_id": str(run.id), "action": "code_agent_failed"},
        )
    else:
        preview_url = _safe_result_url(result.get("preview_url"))
        repo_url = _safe_result_url(result.get("repo_url"))
        run.status = "success"
        run.workspace_path = str(result.get("workspace_path") or "")[:500]
        run.save(update_fields=["status", "result", "log", "workspace_path", "finished_at", "updated_at"])
        if preview_url:
            project.preview_url = preview_url
        if repo_url:
            project.repo_url = repo_url
        if result.get("repo_name"):
            project.repo_name = str(result.get("repo_name"))[:220]
        project.status = "preview"
        project.last_build_error = ""
        project.save(update_fields=["preview_url", "repo_url", "repo_name", "status", "last_build_error", "updated_at"])
        if deployment:
            deployment.mark_success(project.preview_url, str(result.get("checksum") or "")[:128])
        Message.objects.create(
            conversation=project.conversation,
            role="assistant",
            content="The isolated Code Agent build is ready. Review the preview before publishing.",
            metadata={
                "sandbox_run_id": str(run.id),
                "action": "code_agent_preview_ready",
                "preview_url": project.preview_url,
            },
        )

    AuditEvent.objects.create(
        organization=project.organization,
        user=run.requested_by,
        project=project,
        action=f"code_agent_{status}",
        payload={"sandbox_run_id": str(run.id)},
    )
    return run
