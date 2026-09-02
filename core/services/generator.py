import hashlib
import json
import shutil
from pathlib import Path
from django.conf import settings
from .ai import sanitize_spec
from managed_backend.security import active_features


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _runtime_source():
    return "\n".join(
        (Path(__file__).parent / name).read_text(encoding="utf-8")
        for name in ("runtime-1.js", "runtime-2.js", "runtime-3.js")
    )


def _runtime_css():
    return (Path(__file__).parent / "runtime.css").read_text(encoding="utf-8")


def _runtime_spec(project):
    spec = sanitize_spec(project.app_spec)
    requested = [str(item) for item in (project.backend_features or []) if item]
    spec["backend"] = {
        "api_version": 1,
        "api_base": f"{settings.APP_PUBLIC_URL}/api/apps/{project.slug}",
        "features": active_features(project),
        "requested_features": requested,
    }
    return spec


def _html(project):
    spec = _runtime_spec(project)
    title = spec["app"]["title"].replace("<", "&lt;").replace(">", "&gt;")
    tagline = spec["app"]["tagline"].replace("<", "&lt;").replace(">", "&gt;")
    language = spec["app"].get("language", "de")
    direction = spec["app"].get("direction", "ltr")
    spec_json = json.dumps(spec, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{language}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="{spec['brand']['primary']}">
<meta name="description" content="{tagline}">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="stylesheet" href="styles.css">
<title>{title}</title>
</head>
<body>
<div id="app"></div>
<script>window.APP_SPEC={spec_json};window.APP_BUILD_VERSION={project.version};window.APP_CACHE_PREFIX={json.dumps(project.slug)};</script>
<script src="app.js"></script>
</body>
</html>"""


def _icon_svg(primary, accent):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{primary}"/><stop offset="1" stop-color="{accent}"/></linearGradient></defs><rect width="512" height="512" rx="118" fill="url(#g)"/><path d="M144 338 232 126h50l87 212h-53l-20-53h-82l-20 53h-50Zm88-99h47l-23-64-24 64Z" fill="white"/><path d="M354 132h26v47h47v26h-47v47h-26v-47h-47v-26h47v-47Z" fill="white"/></svg>"""


def _service_worker(project):
    cache = f"{project.slug}-v{project.version}"
    return f"""const CACHE={json.dumps(cache)};const ASSETS=['./','index.html','styles.css','app.js','manifest.webmanifest','icon.svg'];self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));self.addEventListener('fetch',e=>{{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).then(r=>{{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r;}}).catch(()=>caches.match(e.request).then(r=>r||caches.match('./'))));}});"""


def generate_preview(project):
    spec = _runtime_spec(project)
    project.app_spec = sanitize_spec(project.app_spec)
    project.save(update_fields=["app_spec", "updated_at"])
    root = Path(settings.APP_DATA_ROOT) / "preview" / project.slug
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    _write(root / "index.html", _html(project))
    _write(root / "styles.css", _runtime_css())
    _write(root / "app.js", _runtime_source())
    _write(
        root / "icon.svg",
        _icon_svg(spec["brand"]["primary"], spec["brand"]["accent"]),
    )
    manifest = {
        "name": spec["app"]["title"],
        "short_name": spec["app"]["title"][:24],
        "description": spec["app"]["tagline"],
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": spec["brand"]["background"],
        "theme_color": spec["brand"]["primary"],
        "icons": [
            {
                "src": "icon.svg",
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any maskable",
            }
        ],
    }
    _write(
        root / "manifest.webmanifest",
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )
    _write(root / "sw.js", _service_worker(project))
    checksum = hashlib.sha256(
        "".join(
            path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*"))
            if path.is_file()
        ).encode()
    ).hexdigest()
    return root, checksum


def publish_project(project):
    source = Path(settings.APP_DATA_ROOT) / "preview" / project.slug
    target = Path(settings.APP_DATA_ROOT) / "live" / project.slug
    if not source.exists():
        raise FileNotFoundError("Preview build does not exist")
    if target.exists():
        backup = (
            Path(settings.APP_DATA_ROOT)
            / "backups"
            / project.slug
            / f"v{project.version}"
        )
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(target, backup)
        shutil.rmtree(target)
    shutil.copytree(source, target)
    checksum = hashlib.sha256(
        "".join(
            path.read_text(encoding="utf-8")
            for path in sorted(target.rglob("*"))
            if path.is_file()
        ).encode()
    ).hexdigest()
    return target, checksum
