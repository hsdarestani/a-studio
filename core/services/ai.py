import json
import re
from copy import deepcopy
from django.conf import settings
from openai import OpenAI

DEFAULT_SPEC = {
    "app": {"title": "My App", "tagline": "Everything you need, in one place.", "language": "de", "direction": "ltr"},
    "brand": {"primary": "#6c5ce7", "accent": "#00d2d3", "background": "#f7f8fc", "surface": "#ffffff", "text": "#181a24"},
    "features": ["contact"],
    "navigation": ["home", "services", "contact"],
    "sections": [
        {"type": "hero", "title": "Welcome", "text": "Your new digital experience.", "button": "Get started"},
        {"type": "services", "title": "Our services", "items": [{"title": "Service one", "text": "Describe your first service."}]},
        {"type": "contact", "title": "Contact", "phone": "", "email": "", "address": ""},
    ],
}

SYSTEM_PROMPT = """You are the product architect and UI engineer inside A+ Studio, an AI PWA factory for German businesses.
Return ONLY valid JSON, without markdown. You modify a declarative app specification, not arbitrary executable code.
The result schema is:
{
  "action": "clarify" | "apply",
  "message": "clear user-facing reply in the project's language",
  "feature_title": "short title",
  "feature_description": "what changed and acceptance criteria",
  "spec": {complete app specification}
}
The complete spec must preserve useful existing data. Allowed top-level keys: app, brand, features, navigation, sections.
Allowed section types: hero, services, products, booking, gallery, about, contact, testimonials, faq, loyalty, form, notice.
Use concise, realistic business copy. Never include scripts, HTML, iframe, external code, secrets, tracking IDs, or executable content.
For unclear or risky requests return action=clarify and keep the existing spec unchanged.
For Persian set direction=rtl; otherwise ltr. Favor mobile-first layouts and accessible contrast.
"""


def initial_spec(name, business_type, description, language):
    spec = deepcopy(DEFAULT_SPEC)
    spec["app"].update({"title": name, "language": language, "direction": "rtl" if language == "fa" else "ltr"})
    spec["app"]["tagline"] = description[:180]
    spec["sections"][0]["title"] = name
    spec["sections"][0]["text"] = description[:260]
    spec["sections"][1]["title"] = {"de": "Unsere Leistungen", "fa": "خدمات ما"}.get(language, "Our services")
    spec["business_type"] = business_type
    return sanitize_spec(spec)


def _extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("AI response did not contain JSON")
    return json.loads(text[start:end + 1])


def sanitize_spec(spec):
    source = spec if isinstance(spec, dict) else {}
    result = deepcopy(DEFAULT_SPEC)
    app = source.get("app", {}) if isinstance(source.get("app", {}), dict) else {}
    brand = source.get("brand", {}) if isinstance(source.get("brand", {}), dict) else {}
    result["app"].update({k: str(v)[:500] for k, v in app.items() if k in {"title", "tagline", "language", "direction"}})
    result["brand"].update({k: str(v)[:32] for k, v in brand.items() if k in {"primary", "accent", "background", "surface", "text"}})
    result["features"] = [str(x)[:60] for x in source.get("features", [])[:30] if isinstance(x, (str, int))]
    result["navigation"] = [str(x)[:60] for x in source.get("navigation", [])[:10] if isinstance(x, (str, int))]
    allowed = {"hero", "services", "products", "booking", "gallery", "about", "contact", "testimonials", "faq", "loyalty", "form", "notice"}
    sections = []
    for raw in source.get("sections", [])[:24]:
        if not isinstance(raw, dict) or raw.get("type") not in allowed:
            continue
        clean = {"type": raw["type"]}
        for key, value in raw.items():
            if key == "type":
                continue
            if isinstance(value, str):
                clean[key] = value[:2000]
            elif isinstance(value, (int, float, bool)):
                clean[key] = value
            elif isinstance(value, list):
                items = []
                for item in value[:30]:
                    if isinstance(item, dict):
                        items.append({str(k)[:50]: (str(v)[:800] if not isinstance(v, (int, float, bool)) else v) for k, v in list(item.items())[:12]})
                    elif isinstance(item, str):
                        items.append(item[:800])
                clean[key] = items
        sections.append(clean)
    result["sections"] = sections or deepcopy(DEFAULT_SPEC["sections"])
    return result


def propose_change(project, user_message, history):
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    current = sanitize_spec(project.app_spec or initial_spec(project.name, project.business_type, project.description, project.language))
    context = {
        "project": {"name": project.name, "business_type": project.business_type, "description": project.description, "language": project.language},
        "current_spec": current,
        "recent_messages": history[-10:],
        "request": user_message,
    }
    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,
        input=json.dumps(context, ensure_ascii=False),
    )
    payload = _extract_json(response.output_text)
    action = payload.get("action", "clarify")
    if action not in {"clarify", "apply"}:
        action = "clarify"
    return {
        "action": action,
        "message": str(payload.get("message") or "I need a little more detail.")[:4000],
        "feature_title": str(payload.get("feature_title") or "App update")[:220],
        "feature_description": str(payload.get("feature_description") or user_message)[:4000],
        "spec": sanitize_spec(payload.get("spec") or current),
    }
