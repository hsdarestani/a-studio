import hashlib
import re
import uuid
from pathlib import Path

from django.conf import settings


_BLOCKED_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "image/svg+xml",
    "application/javascript",
    "text/javascript",
    "application/x-sh",
    "application/x-msdownload",
    "application/x-executable",
}
_BLOCKED_SUFFIXES = {
    ".html", ".htm", ".xhtml", ".svg", ".js", ".mjs", ".cjs",
    ".exe", ".dll", ".com", ".scr", ".msi", ".bat", ".cmd",
    ".sh", ".bash", ".zsh", ".ps1", ".php", ".phar",
}
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


def storage_root():
    root = Path(settings.APP_DATA_ROOT) / "managed-storage"
    root.mkdir(parents=True, exist_ok=True)
    return root


def clean_original_name(value):
    name = Path(str(value or "file")).name
    name = _SAFE_NAME.sub("_", name).strip(" ._")[:180]
    return name or "file"


def validate_upload(upload):
    max_bytes = int(getattr(settings, "MANAGED_STORAGE_MAX_BYTES", 10 * 1024 * 1024))
    size = int(getattr(upload, "size", 0) or 0)
    if size <= 0:
        raise ValueError("empty_file")
    if size > max_bytes:
        raise ValueError("file_too_large")
    original_name = clean_original_name(getattr(upload, "name", "file"))
    content_type = str(getattr(upload, "content_type", "") or "application/octet-stream").lower().split(";", 1)[0].strip()
    if content_type in _BLOCKED_TYPES or Path(original_name).suffix.lower() in _BLOCKED_SUFFIXES:
        raise ValueError("file_type_blocked")
    return original_name, content_type, size


def save_upload(project, user, upload):
    original_name, content_type, size = validate_upload(upload)
    file_id = uuid.uuid4()
    suffix = Path(original_name).suffix.lower()[:12]
    relative = Path(str(project.id)) / str(user.id) / f"{file_id.hex}{suffix}"
    target = storage_root() / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    written = 0
    try:
        with target.open("xb") as handle:
            for chunk in upload.chunks():
                written += len(chunk)
                if written > int(getattr(settings, "MANAGED_STORAGE_MAX_BYTES", 10 * 1024 * 1024)):
                    raise ValueError("file_too_large")
                digest.update(chunk)
                handle.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if written != size:
        size = written
    return file_id, relative.as_posix(), original_name, content_type, size, digest.hexdigest()


def resolve_storage_key(storage_key):
    root = storage_root().resolve()
    target = (root / str(storage_key)).resolve()
    if target == root or root not in target.parents:
        raise ValueError("invalid_storage_key")
    return target


def delete_storage_key(storage_key):
    try:
        resolve_storage_key(storage_key).unlink(missing_ok=True)
    except ValueError:
        return
