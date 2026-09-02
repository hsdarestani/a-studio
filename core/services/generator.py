import hashlib
import html
import json
import shutil
from pathlib import Path
from django.conf import settings
from managed_backend.security import active_features
from .ai import sanitize_spec


RUNTIME_DIR = Path(__file__).resolve().parent


def _safe(value):
    return html.escape(str(value or ""), quote=True)


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _runtime_asset(name):
    return (RUNTIME_DIR / name).read_text(encoding="utf-8")


def _icon_svg(primary, accent):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{_safe(primary)}"/><stop offset="1" stop-color="{_safe(accent)}"/></linearGradient></defs><rect width="512" height="512" rx="112" fill="url(#g)"/><path d="M154 342 256 142l102 200h-58l-17-38h-55l25-52h8l-5-12-52 102z" fill="white"/></svg>'''


def _index_html(spec, version, slug):
    app, brand = spec["app"], spec["brand"]
    title = _safe(app.get("title"))
    direction = "rtl" if app.get("direction") == "rtl" else "ltr"
    language = _safe(app.get("language", "de"))
    version = str(version)
    cache_prefix = f"astudio-{slug}-"
    runtime_config = (
        "window.APP_BUILD_VERSION = "
        + json.dumps(version)
        + "; window.APP_CACHE_PREFIX = "
        + json.dumps(cache_prefix)
        + ";"
    )
    return f'''<!doctype html>
<html lang="{language}" dir="{direction}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="{_safe(brand.get('primary'))}">
  <meta name="description" content="{_safe(app.get('tagline'))}">
  <link rel="manifest" href="manifest.webmanifest?v={version}">
  <link rel="icon" href="icon.svg?v={version}" type="image/svg+xml">
  <link rel="apple-touch-icon" href="icon.svg?v={version}">
  <link rel="stylesheet" href="styles.css?v={version}">
  <title>{title}</title>
</head>
<body>
  <div id="app" class="app-shell" aria-live="polite"></div>
  <noscript>This app needs JavaScript enabled.</noscript>
  <script>{runtime_config}</script>
  <script src="config.js?v={version}"></script>
  <script src="app.js?v={version}"></script>
</body>
</html>'''


def _styles(spec):
    brand = spec["brand"]
    variables = (
        ":root{"
        f"--primary:{brand.get('primary')};"
        f"--accent:{brand.get('accent')};"
        f"--bg:{brand.get('background')};"
        f"--surface:{brand.get('surface')};"
        f"--text:{brand.get('text')};"
        "--muted:#667085;"
        "--line:rgba(127,127,127,.16);"
        "--success:#16a66a;"
        "--radius:24px;"
        "--shadow:0 20px 60px rgba(17,24,39,.12)"
        "}\n"
    )
    return variables + _runtime_asset("runtime.css")


def _app_js():
    return "\n".join(
        _runtime_asset(name)
        for name in ("runtime-1.js", "runtime-2.js", "runtime-3.js")
    )


def _service_worker(project):
    version = str(project.version)
    prefix = f"astudio-{project.slug}-"
    cache_name = f"{prefix}v{version}"
    assets = [
        "./",
        "index.html",
        f"styles.css?v={version}",
        f"app.js?v={version}",
        f"config.js?v={version}",
        f"manifest.webmanifest?v={version}",
        f"icon.svg?v={version}",
    ]
    return (
        "const P="
        + json.dumps(prefix)
        + ";const C="
        + json.dumps(cache_name)
        + ";const A="
        + json.dumps(assets)
        + ";"
        "self.addEventListener('install',e=>e.waitUntil(caches.open(C).then(c=>c.addAll(A))));"
        "self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x.startsWith(P)&&x!==C).map(x=>caches.delete(x))))));"
        "self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).catch(()=>caches.match('index.html'))));});"
    )


def _runtime_spec(project):
    spec = sanitize_spec(project.app_spec)
    requested = [str(item) for item in (project.backend_features or [])]
    spec["backend"] = {
        "api_version": 1,
        "api_base": f"{settings.APP_PUBLIC_URL}/api/apps/{project.slug}",
        "features": active_features(project),
        "requested_features": requested,
    }
    return spec


def generate_preview(project):
    spec = _runtime_spec(project)
    root = Path(settings.APP_DATA_ROOT) / "preview" / project.slug
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    _write(root / "index.html", _index_html(spec, project.version, project.slug))
    _write(root / "styles.css", _styles(spec))
    _write(root / "app.js", _app_js())
    _write(
        root / "config.js",
        "window.APP_SPEC = "
        + json.dumps(spec, ensure_ascii=False).replace("</", "<\\/")
        + ";",
    )
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
            for path in sorted(root.glob("*"))
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
            for path in sorted(target.glob("*"))
            if path.is_file()
        ).encode()
    ).hexdigest()
    return target, checksum
