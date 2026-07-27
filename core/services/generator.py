import hashlib
import html
import json
import shutil
from pathlib import Path
from django.conf import settings
from .ai import sanitize_spec


def _safe(value):
    return html.escape(str(value or ""), quote=True)


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _icon_svg(primary, accent):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{_safe(primary)}"/><stop offset="1" stop-color="{_safe(accent)}"/></linearGradient></defs><rect width="512" height="512" rx="112" fill="url(#g)"/><path d="M154 342 256 142l102 200h-58l-17-38h-55l25-52h8l-5-12-52 102z" fill="white"/></svg>'''


def _index_html(spec):
    app, brand = spec["app"], spec["brand"]
    title = _safe(app.get("title"))
    direction = "rtl" if app.get("direction") == "rtl" else "ltr"
    language = _safe(app.get("language", "de"))
    return f'''<!doctype html>
<html lang="{language}" dir="{direction}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="{_safe(brand.get('primary'))}">
  <meta name="description" content="{_safe(app.get('tagline'))}">
  <link rel="manifest" href="manifest.webmanifest">
  <link rel="icon" href="icon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="icon.svg">
  <link rel="stylesheet" href="styles.css">
  <title>{title}</title>
</head>
<body>
  <div id="app" class="app-shell" aria-live="polite"></div>
  <noscript>This app needs JavaScript enabled.</noscript>
  <script src="config.js"></script>
  <script src="app.js"></script>
</body>
</html>'''


def _styles(spec):
    b = spec["brand"]
    return f''':root{{--primary:{b.get('primary')};--accent:{b.get('accent')};--bg:{b.get('background')};--surface:{b.get('surface')};--text:{b.get('text')};--muted:#6b7280;--radius:22px;--shadow:0 18px 55px rgba(17,24,39,.12)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.55}}button,input,textarea,select{{font:inherit}}a{{color:inherit}}.app-shell{{min-height:100vh;padding-bottom:86px}}.topbar{{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;padding:15px 20px;background:color-mix(in srgb,var(--surface) 88%,transparent);backdrop-filter:blur(18px);border-bottom:1px solid rgba(127,127,127,.14)}}.brand{{display:flex;gap:11px;align-items:center;font-weight:850}}.brand-mark{{width:38px;height:38px;border-radius:13px;background:linear-gradient(135deg,var(--primary),var(--accent));display:grid;place-items:center;color:white;font-weight:900;box-shadow:0 10px 30px color-mix(in srgb,var(--primary) 28%,transparent)}}.install{{border:0;background:var(--text);color:var(--surface);padding:9px 14px;border-radius:999px;font-weight:750;cursor:pointer}}main{{max-width:980px;margin:auto;padding:18px}}section{{margin:18px 0;background:var(--surface);border-radius:var(--radius);padding:24px;box-shadow:var(--shadow);overflow:hidden}}.hero{{position:relative;min-height:360px;display:flex;flex-direction:column;justify-content:flex-end;background:linear-gradient(145deg,color-mix(in srgb,var(--primary) 94%,white),color-mix(in srgb,var(--accent) 74%,var(--primary)));color:white}}.hero:before{{content:"";position:absolute;width:300px;height:300px;border-radius:50%;right:-90px;top:-100px;background:rgba(255,255,255,.14);filter:blur(2px)}}h1{{font-size:clamp(2.2rem,8vw,4.8rem);line-height:.98;letter-spacing:-.055em;margin:0 0 16px;max-width:760px}}h2{{font-size:clamp(1.45rem,4vw,2.35rem);letter-spacing:-.035em;margin:0 0 16px}}p{{margin:0 0 14px}}.lead{{font-size:1.08rem;max-width:640px;opacity:.92}}.cta{{display:inline-flex;align-items:center;justify-content:center;width:max-content;text-decoration:none;border:0;border-radius:999px;padding:13px 19px;background:white;color:#111827;font-weight:850;margin-top:12px;cursor:pointer}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}.card{{border:1px solid rgba(127,127,127,.16);border-radius:18px;padding:17px;background:color-mix(in srgb,var(--surface) 96%,var(--primary))}}.card h3{{margin:0 0 7px}}.price{{font-weight:900;color:var(--primary);font-size:1.05rem}}.pill{{display:inline-flex;padding:6px 10px;border-radius:999px;background:color-mix(in srgb,var(--primary) 12%,transparent);color:var(--primary);font-weight:750;font-size:.82rem}}.booking,.contact-form{{display:grid;gap:12px}}label{{font-weight:700;font-size:.9rem}}input,textarea,select{{width:100%;padding:13px 14px;border-radius:14px;border:1px solid rgba(127,127,127,.28);background:var(--surface);color:var(--text);outline:none}}input:focus,textarea:focus,select:focus{{border-color:var(--primary);box-shadow:0 0 0 4px color-mix(in srgb,var(--primary) 14%,transparent)}}.primary-button{{border:0;border-radius:14px;padding:13px 16px;background:linear-gradient(135deg,var(--primary),var(--accent));color:white;font-weight:850;cursor:pointer}}.gallery{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}.gallery-item{{aspect-ratio:1;border-radius:17px;background:linear-gradient(145deg,color-mix(in srgb,var(--primary) 18%,white),color-mix(in srgb,var(--accent) 20%,white));display:grid;place-items:center;font-size:2rem}}.faq details{{padding:14px 0;border-bottom:1px solid rgba(127,127,127,.18)}}.faq summary{{cursor:pointer;font-weight:800}}.notice{{border-inline-start:5px solid var(--accent)}}.bottom-nav{{position:fixed;z-index:30;bottom:12px;left:50%;transform:translateX(-50%);width:min(calc(100% - 24px),620px);display:flex;justify-content:space-around;gap:6px;padding:8px;background:color-mix(in srgb,var(--surface) 90%,transparent);backdrop-filter:blur(22px);border:1px solid rgba(127,127,127,.16);border-radius:22px;box-shadow:var(--shadow)}}.bottom-nav a{{text-decoration:none;font-size:.78rem;font-weight:750;padding:8px 10px;border-radius:14px;color:var(--muted)}}.bottom-nav a.active{{background:color-mix(in srgb,var(--primary) 12%,transparent);color:var(--primary)}}.toast{{position:fixed;top:74px;left:50%;transform:translateX(-50%);z-index:50;background:#111827;color:white;padding:12px 16px;border-radius:14px;box-shadow:var(--shadow)}}.hidden{{display:none!important}}@media(min-width:720px){{main{{padding:30px}}section{{padding:34px}}.gallery{{grid-template-columns:repeat(4,1fr)}}}}
'''


def _app_js():
    return r'''(() => {
const spec = window.APP_SPEC || {};
const app = spec.app || {}, sections = spec.sections || [];
const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const items = value => Array.isArray(value) ? value : [];
let deferredPrompt;
const section = (s, i) => {
  const id = esc(s.id || s.type || `section-${i}`);
  const title = s.title ? `<h2>${esc(s.title)}</h2>` : '';
  if (s.type === 'hero') return `<section id="${id}" class="hero"><h1>${esc(s.title || app.title)}</h1><p class="lead">${esc(s.text || app.tagline)}</p>${s.button ? `<a class="cta" href="#${esc(s.target || 'services')}">${esc(s.button)}</a>` : ''}</section>`;
  if (['services','products'].includes(s.type)) return `<section id="${id}">${title}<div class="grid">${items(s.items).map(x => `<article class="card"><span class="pill">${esc(x.category || (s.type === 'products' ? 'Product' : 'Service'))}</span><h3>${esc(x.title)}</h3><p>${esc(x.text || x.description)}</p>${x.price ? `<div class="price">${esc(x.price)}</div>` : ''}</article>`).join('')}</div></section>`;
  if (s.type === 'booking') return `<section id="${id}">${title}<p>${esc(s.text || '')}</p><form class="booking" data-local-form><label>${esc(s.name_label || 'Name')}<input name="name" required></label><label>${esc(s.service_label || 'Service')}<select name="service">${items(s.services).map(x => `<option>${esc(x.title || x)}</option>`).join('')}</select></label><label>${esc(s.date_label || 'Preferred date')}<input name="date" type="date" required></label><button class="primary-button">${esc(s.button || 'Request appointment')}</button></form></section>`;
  if (s.type === 'gallery') return `<section id="${id}">${title}<div class="gallery">${items(s.items).map((x,n) => `<div class="gallery-item" aria-label="${esc(x.title || `Image ${n+1}`)}">${esc(x.emoji || '✦')}</div>`).join('')}</div></section>`;
  if (s.type === 'testimonials') return `<section id="${id}">${title}<div class="grid">${items(s.items).map(x => `<blockquote class="card"><p>“${esc(x.text)}”</p><strong>${esc(x.name)}</strong></blockquote>`).join('')}</div></section>`;
  if (s.type === 'faq') return `<section id="${id}" class="faq">${title}${items(s.items).map(x => `<details><summary>${esc(x.question)}</summary><p>${esc(x.answer)}</p></details>`).join('')}</section>`;
  if (s.type === 'loyalty') return `<section id="${id}">${title}<div class="card"><span class="pill">${esc(s.label || 'Member benefits')}</span><h3>${esc(s.headline || 'Your loyalty card')}</h3><p>${esc(s.text || '')}</p><div class="price">${esc(s.points || '0 points')}</div></div></section>`;
  if (s.type === 'form') return `<section id="${id}">${title}<form class="contact-form" data-local-form>${items(s.fields).map(f => `<label>${esc(f.label)}<input name="${esc(f.name || f.label)}" type="${esc(f.type || 'text')}" ${f.required ? 'required' : ''}></label>`).join('')}<button class="primary-button">${esc(s.button || 'Send')}</button></form></section>`;
  if (s.type === 'contact') return `<section id="${id}">${title}<div class="grid"><div class="card"><h3>${esc(s.company || app.title)}</h3><p>${esc(s.address || '')}</p>${s.phone ? `<p><a href="tel:${esc(s.phone)}">${esc(s.phone)}</a></p>` : ''}${s.email ? `<p><a href="mailto:${esc(s.email)}">${esc(s.email)}</a></p>` : ''}</div></div></section>`;
  return `<section id="${id}" class="${s.type === 'notice' ? 'notice' : ''}">${title}<p>${esc(s.text || s.description || '')}</p></section>`;
};
const nav = items(spec.navigation).slice(0,5);
document.getElementById('app').innerHTML = `<header class="topbar"><div class="brand"><div class="brand-mark">A+</div><span>${esc(app.title || 'App')}</span></div><button id="install" class="install hidden">Install</button></header><main>${sections.map(section).join('')}</main>${nav.length ? `<nav class="bottom-nav">${nav.map((x,i) => `<a href="#${esc(x)}" class="${i===0?'active':''}">${esc(x.replace(/[-_]/g,' '))}</a>`).join('')}</nav>` : ''}`;
window.addEventListener('beforeinstallprompt', e => {e.preventDefault(); deferredPrompt=e; document.getElementById('install')?.classList.remove('hidden')});
document.getElementById('install')?.addEventListener('click', async () => {if(deferredPrompt){deferredPrompt.prompt(); await deferredPrompt.userChoice; deferredPrompt=null}});
document.querySelectorAll('[data-local-form]').forEach(form => form.addEventListener('submit', e => {e.preventDefault(); const t=document.createElement('div');t.className='toast';t.textContent=app.language==='de'?'Danke! Ihre Anfrage wurde gespeichert.':app.language==='fa'?'ممنون! درخواست شما ثبت شد.':'Thanks! Your request was saved.';document.body.appendChild(t);form.reset();setTimeout(()=>t.remove(),3200)}));
if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('sw.js'));
})();'''


def generate_preview(project):
    spec = sanitize_spec(project.app_spec)
    root = Path(settings.APP_DATA_ROOT) / "preview" / project.slug
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    _write(root / "index.html", _index_html(spec))
    _write(root / "styles.css", _styles(spec))
    _write(root / "app.js", _app_js())
    _write(root / "config.js", "window.APP_SPEC = " + json.dumps(spec, ensure_ascii=False).replace("</", "<\\/") + ";")
    _write(root / "icon.svg", _icon_svg(spec["brand"]["primary"], spec["brand"]["accent"]))
    manifest = {
        "name": spec["app"]["title"], "short_name": spec["app"]["title"][:24], "description": spec["app"]["tagline"],
        "start_url": "./", "scope": "./", "display": "standalone", "background_color": spec["brand"]["background"],
        "theme_color": spec["brand"]["primary"], "icons": [{"src": "icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}],
    }
    _write(root / "manifest.webmanifest", json.dumps(manifest, ensure_ascii=False, indent=2))
    _write(root / "sw.js", "const C='astudio-v" + str(project.version) + "';const A=['./','index.html','styles.css','app.js','config.js','manifest.webmanifest','icon.svg'];self.addEventListener('install',e=>e.waitUntil(caches.open(C).then(c=>c.addAll(A))));self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x))))));self.addEventListener('fetch',e=>e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).catch(()=>caches.match('index.html')))));" )
    checksum = hashlib.sha256("".join(p.read_text(encoding="utf-8") for p in sorted(root.glob("*")) if p.is_file()).encode()).hexdigest()
    return root, checksum


def publish_project(project):
    source = Path(settings.APP_DATA_ROOT) / "preview" / project.slug
    target = Path(settings.APP_DATA_ROOT) / "live" / project.slug
    if not source.exists():
        raise FileNotFoundError("Preview build does not exist")
    if target.exists():
        backup = Path(settings.APP_DATA_ROOT) / "backups" / project.slug / f"v{project.version}"
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(target, backup)
        shutil.rmtree(target)
    shutil.copytree(source, target)
    checksum = hashlib.sha256("".join(p.read_text(encoding="utf-8") for p in sorted(target.glob("*")) if p.is_file()).encode()).hexdigest()
    return target, checksum
