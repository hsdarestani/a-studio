import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings


_TEXT_EXTENSIONS = {
    ".html", ".htm", ".css", ".js", ".mjs", ".json", ".webmanifest", ".md", ".txt", ".svg",
}
_ALLOWED_BASENAMES = {"manifest.webmanifest", "robots.txt"}
_BLOCKED_NAMES = {".env", ".git", ".gitignore", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}
_SAFE_PART = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
_MAX_FILE_BYTES = 512 * 1024
_MAX_FILES = 80
_BLOCKED_CODE_PATTERNS = (
    re.compile(r"\beval\s*\(", re.I),
    re.compile(r"\bnew\s+Function\s*\(", re.I),
    re.compile(r"javascript\s*:", re.I),
    re.compile(r"<script[^>]+src\s*=\s*['\"]https?://", re.I),
)


class CodeWorkspaceError(ValueError):
    pass


def _root(project):
    return Path(settings.APP_DATA_ROOT) / "code-workspaces" / project.slug


def current_root(project):
    return _root(project) / "current"


def revisions_root(project):
    return _root(project) / "revisions"


def _normalize_path(value):
    value = str(value or "").replace("\\", "/").strip().strip("/")
    if not value or len(value) > 240:
        raise CodeWorkspaceError("invalid_path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or not _SAFE_PART.fullmatch(part) for part in parts):
        raise CodeWorkspaceError("invalid_path")
    if any(part.startswith(".") for part in parts):
        raise CodeWorkspaceError("hidden_paths_not_allowed")
    if parts[-1].lower() in _BLOCKED_NAMES:
        raise CodeWorkspaceError("blocked_file")
    suffix = Path(parts[-1]).suffix.lower()
    if suffix not in _TEXT_EXTENSIONS and parts[-1].lower() not in _ALLOWED_BASENAMES:
        raise CodeWorkspaceError("unsupported_file_type")
    return "/".join(parts)


def _target(root, path):
    path = _normalize_path(path)
    root = Path(root).resolve()
    target = (root / path).resolve()
    if root not in target.parents:
        raise CodeWorkspaceError("invalid_path")
    return target, path


def _read_text(path):
    raw = Path(path).read_bytes()
    if len(raw) > _MAX_FILE_BYTES:
        raise CodeWorkspaceError("file_too_large")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CodeWorkspaceError("non_utf8_file") from exc


def _validate_workspace(root):
    root = Path(root)
    index = root / "index.html"
    if not index.is_file():
        raise CodeWorkspaceError("index_required")
    files = [path for path in root.rglob("*") if path.is_file()]
    if len(files) > _MAX_FILES:
        raise CodeWorkspaceError("too_many_files")
    for path in files:
        rel = path.relative_to(root).as_posix()
        _normalize_path(rel)
        content = _read_text(path)
        if path.suffix.lower() in {".html", ".htm", ".js", ".mjs"}:
            if any(pattern.search(content) for pattern in _BLOCKED_CODE_PATTERNS):
                raise CodeWorkspaceError(f"unsafe_code_pattern:{rel}")
        if path.suffix.lower() in {".js", ".mjs"}:
            try:
                result = subprocess.run(
                    ["node", "--check", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                raise CodeWorkspaceError("javascript_validator_unavailable") from exc
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "JavaScript syntax error")[-1200:]
                raise CodeWorkspaceError(f"javascript_syntax_error:{rel}:{detail}")
    return True


def bootstrap_workspace(project):
    root = current_root(project)
    if root.exists() and any(root.rglob("*")):
        return root
    root.mkdir(parents=True, exist_ok=True)
    preview = Path(settings.APP_DATA_ROOT) / "preview" / project.slug
    if preview.exists():
        copied = 0
        for source in sorted(preview.rglob("*")):
            if not source.is_file():
                continue
            rel = source.relative_to(preview).as_posix()
            try:
                target, _ = _target(root, rel)
                content = _read_text(source)
            except CodeWorkspaceError:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            copied += 1
            if copied >= _MAX_FILES:
                break
    if not (root / "index.html").exists():
        (root / "index.html").write_text(
            "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>"
            + project.name.replace("<", "&lt;").replace(">", "&gt;")
            + "</title><link rel=\"stylesheet\" href=\"styles.css\"></head><body><main id=\"app\"><h1>"
            + project.name.replace("<", "&lt;").replace(">", "&gt;")
            + "</h1><p>Code workspace ready.</p></main><script src=\"app.js\"></script></body></html>",
            encoding="utf-8",
        )
        (root / "styles.css").write_text("body{font-family:system-ui,sans-serif;margin:0;padding:2rem;background:#f7f8fc;color:#181a24}", encoding="utf-8")
        (root / "app.js").write_text("console.info('A+ Studio code workspace ready');", encoding="utf-8")
    return root


def list_files(project):
    root = bootstrap_workspace(project)
    output = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        try:
            _normalize_path(rel)
        except CodeWorkspaceError:
            continue
        output.append({"path": rel, "size": path.stat().st_size})
        if len(output) >= _MAX_FILES:
            break
    return output


def read_file(project, path):
    root = bootstrap_workspace(project)
    target, normalized = _target(root, path)
    if not target.is_file():
        raise FileNotFoundError(normalized)
    return normalized, _read_text(target)


def _snapshot(project, label="before-change"):
    source = bootstrap_workspace(project)
    revision = revisions_root(project) / f"v{project.version:06d}-{label}"
    if revision.exists():
        shutil.rmtree(revision)
    revision.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, revision)
    return revision


def apply_changes(project, files, deleted_files=None):
    root = bootstrap_workspace(project)
    files = files if isinstance(files, list) else []
    deleted_files = deleted_files if isinstance(deleted_files, list) else []
    if not files and not deleted_files:
        raise CodeWorkspaceError("no_code_changes")
    if len(files) + len(deleted_files) > 40:
        raise CodeWorkspaceError("too_many_changes")

    normalized_changes = []
    total_bytes = 0
    for item in files:
        if not isinstance(item, dict):
            raise CodeWorkspaceError("invalid_change")
        path = _normalize_path(item.get("path"))
        content = item.get("content")
        if not isinstance(content, str):
            raise CodeWorkspaceError("invalid_content")
        raw = content.encode("utf-8")
        if len(raw) > _MAX_FILE_BYTES:
            raise CodeWorkspaceError("file_too_large")
        total_bytes += len(raw)
        if total_bytes > 2 * 1024 * 1024:
            raise CodeWorkspaceError("change_set_too_large")
        normalized_changes.append((path, content))

    normalized_deletes = [_normalize_path(path) for path in deleted_files]
    if "index.html" in normalized_deletes:
        raise CodeWorkspaceError("index_required")

    snapshot = _snapshot(project)
    staging = Path(tempfile.mkdtemp(prefix="astudio-code-", dir=str(_root(project))))
    try:
        shutil.copytree(root, staging / "current", dirs_exist_ok=True)
        stage_root = staging / "current"
        for path, content in normalized_changes:
            target, _ = _target(stage_root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        for path in normalized_deletes:
            target, _ = _target(stage_root, path)
            target.unlink(missing_ok=True)
        _validate_workspace(stage_root)
        backup = _root(project) / "previous"
        if backup.exists():
            shutil.rmtree(backup)
        if root.exists():
            os.replace(root, backup)
        os.replace(stage_root, root)
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if not root.exists() and snapshot.exists():
            shutil.copytree(snapshot, root)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {"snapshot": str(snapshot), "files_changed": [p for p, _ in normalized_changes], "files_deleted": normalized_deletes}


def deploy_workspace_preview(project):
    source = bootstrap_workspace(project)
    _validate_workspace(source)
    preview = Path(settings.APP_DATA_ROOT) / "preview" / project.slug
    staging = Path(settings.APP_DATA_ROOT) / "preview" / f".{project.slug}-code-staging"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(source, staging)
    digest = hashlib.sha256()
    for path in sorted(p for p in staging.rglob("*") if p.is_file()):
        rel = path.relative_to(staging).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    if preview.exists():
        shutil.rmtree(preview)
    os.replace(staging, preview)
    return preview, digest.hexdigest()


def workspace_manifest(project):
    files = list_files(project)
    return {
        "project_id": str(project.id),
        "version": project.version,
        "files": files,
        "entry": "index.html",
        "mode": "code_workspace",
    }


def export_context(project, max_chars=120_000):
    chunks = []
    used = 0
    for item in list_files(project):
        path = item["path"]
        try:
            _, content = read_file(project, path)
        except (FileNotFoundError, CodeWorkspaceError):
            continue
        chunk = f"\n--- FILE: {path} ---\n{content}\n"
        if used + len(chunk) > max_chars:
            break
        chunks.append(chunk)
        used += len(chunk)
    return "".join(chunks)
