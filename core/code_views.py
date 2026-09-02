import difflib
import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from .models import Deployment, FeatureRequest, Project
from .services.code_workspace import (
    CodeWorkspaceError,
    apply_changes,
    deploy_workspace_preview,
    list_files,
    read_file,
    revisions_root,
    workspace_manifest,
)
from .services.github import sync_project_repository


def _project_for(user, pk):
    return get_object_or_404(
        Project.objects.select_related("organization"),
        pk=pk,
        organization__memberships__user=user,
    )


def _require_code(project):
    if project.builder_mode != "code_agent":
        return JsonResponse({"error": "code_workspace_not_enabled"}, status=404)
    return None


@login_required
@require_GET
def code_manifest(request, pk):
    project = _project_for(request.user, pk)
    blocked = _require_code(project)
    if blocked:
        return blocked
    return JsonResponse(workspace_manifest(project))


@login_required
@require_GET
def code_file(request, pk):
    project = _project_for(request.user, pk)
    blocked = _require_code(project)
    if blocked:
        return blocked
    try:
        path, content = read_file(project, request.GET.get("path", ""))
    except FileNotFoundError:
        return JsonResponse({"error": "file_not_found"}, status=404)
    except CodeWorkspaceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"path": path, "content": content, "version": project.version})


@login_required
@require_POST
def code_file_save(request, pk):
    project = _project_for(request.user, pk)
    blocked = _require_code(project)
    if blocked:
        return blocked
    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "invalid_json"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "invalid_json"}, status=400)
    path = str(payload.get("path") or "")
    content = payload.get("content")
    if not isinstance(content, str):
        return JsonResponse({"error": "content_required"}, status=400)

    next_version = project.version + 1
    deployment = Deployment.objects.create(
        project=project,
        environment="preview",
        status="building",
        version=next_version,
        url=project.preview_url,
    )
    try:
        result = apply_changes(project, [{"path": path, "content": content}], [])
        root, checksum = deploy_workspace_preview(project)
        with transaction.atomic():
            locked = Project.objects.select_for_update().get(pk=project.pk)
            locked.version = max(locked.version + 1, next_version)
            locked.status = "preview"
            locked.last_build_error = ""
            locked.save(update_fields=["version", "status", "last_build_error", "updated_at"])
            project = locked
        repo_sync_error = ""
        if settings.GITHUB_TOKEN:
            try:
                sync_project_repository(project, root)
            except Exception as exc:
                repo_sync_error = str(exc)[:1000]
        feature = FeatureRequest.objects.create(
            project=project,
            requested_by=request.user,
            title=f"Manual code edit · {path}"[:220],
            description="Manual edit saved from A+ Studio Code IDE.",
            size="micro",
            credits=0,
            status="done",
            before_spec={"mode": "code_workspace", "snapshot": result.get("snapshot", "")},
            after_spec={
                "mode": "code_workspace",
                "version": project.version,
                "changed_files": [path],
                "files": list_files(project),
                "snapshot": result.get("snapshot", ""),
                "repo_sync_error": repo_sync_error,
            },
        )
        deployment.version = project.version
        if repo_sync_error:
            deployment.log = f"Preview succeeded; repository sync pending: {repo_sync_error}"
        deployment.mark_success(project.preview_url, checksum)
        return JsonResponse(
            {
                "ok": True,
                "version": project.version,
                "preview_url": project.preview_url,
                "feature_id": str(feature.id),
                "changed_files": [path],
                "repo_sync_error": repo_sync_error,
            }
        )
    except CodeWorkspaceError as exc:
        deployment.status = "failed"
        deployment.log = str(exc)
        deployment.save(update_fields=["status", "log", "updated_at"])
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception as exc:
        deployment.status = "failed"
        deployment.log = str(exc)[:4000]
        deployment.save(update_fields=["status", "log", "updated_at"])
        return JsonResponse({"error": "save_failed"}, status=500)


@login_required
@require_GET
def code_changes(request, pk):
    project = _project_for(request.user, pk)
    blocked = _require_code(project)
    if blocked:
        return blocked
    features = project.feature_requests.filter(after_spec__mode="code_workspace").order_by("-created_at")[:20]
    items = []
    for feature in features:
        after = feature.after_spec or {}
        items.append(
            {
                "id": str(feature.id),
                "title": feature.title,
                "description": feature.description,
                "version": after.get("version"),
                "changed_files": after.get("changed_files") or [],
                "deleted_files": after.get("deleted_files") or [],
                "created_at": feature.created_at.isoformat(),
            }
        )
    return JsonResponse({"changes": items, "current_version": project.version})


@login_required
@require_GET
def code_diff(request, pk, feature_id):
    project = _project_for(request.user, pk)
    blocked = _require_code(project)
    if blocked:
        return blocked
    feature = get_object_or_404(FeatureRequest, pk=feature_id, project=project)
    after = feature.after_spec or {}
    snapshot_value = str(after.get("snapshot") or (feature.before_spec or {}).get("snapshot") or "")
    if not snapshot_value:
        return JsonResponse({"error": "snapshot_unavailable"}, status=404)
    revisions = revisions_root(project).resolve()
    snapshot = Path(snapshot_value).resolve()
    if revisions not in snapshot.parents or not snapshot.is_dir():
        return JsonResponse({"error": "snapshot_unavailable"}, status=404)

    paths = []
    for path in (after.get("changed_files") or []) + (after.get("deleted_files") or []):
        path = str(path)
        if path and path not in paths:
            paths.append(path)
    chunks = []
    for path in paths[:20]:
        old_path = snapshot / path
        try:
            old = old_path.read_text(encoding="utf-8").splitlines() if old_path.is_file() else []
        except (UnicodeDecodeError, OSError):
            old = []
        try:
            _normalized, current = read_file(project, path)
            new = current.splitlines()
        except (FileNotFoundError, CodeWorkspaceError):
            new = []
        diff = difflib.unified_diff(old, new, fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="")
        text = "\n".join(diff)
        if text:
            chunks.append(text[:80_000])
    return JsonResponse({"feature_id": str(feature.id), "diff": "\n\n".join(chunks)[:160_000]})
