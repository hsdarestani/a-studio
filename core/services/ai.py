import json
import re
from copy import deepcopy
from django.conf import settings
from openai import OpenAI


DEFAULT_SPEC = {
    "app": {
        "title": "My App",
        "tagline": "Everything you need, in one place.",
        "language": "de",
        "direction": "ltr",
    },
    "brand": {
        "primary": "#6c5ce7",
        "accent": "#00d2d3",
        "background": "#f7f8fc",
        "surface": "#ffffff",
        "text": "#181a24",
    },
    "features": ["contact"],
    "navigation": ["home", "services", "contact"],
    "sections": [
        {
            "type": "hero",
            "title": "Welcome",
            "text": "Your new digital experience.",
            "button": "Get started",
        },
        {
            "type": "services",
            "title": "Our services",
            "items": [{"title": "Service one", "text": "Describe your first service."}],
        },
        {"type": "contact", "title": "Contact", "phone": "", "email": "", "address": ""},
    ],
}


SYSTEM_PROMPT = """You are the product architect and interaction designer inside A+ Studio, an AI PWA factory for German businesses.
Return ONLY valid JSON, without markdown. You modify a declarative application specification, never executable code.

Result schema:
{
  "action": "clarify" | "apply",
  "message": "clear user-facing reply in the project's language",
  "feature_title": "short title",
  "feature_description": "what changed and acceptance criteria",
  "spec": {complete application specification}
}

The complete spec must preserve useful existing data.
Allowed top-level keys: app, brand, features, navigation, sections.
Allowed section types: hero, services, products, booking, gallery, about, contact, testimonials, faq, loyalty, form, notice, recommendation_quiz.

For recommendation, matching, onboarding, assessment, configurator or personality-based apps, you MUST build an actual interactive experience with a recommendation_quiz section instead of describing the feature in ordinary text.
Use this structure:
{
  "type": "recommendation_quiz",
  "title": "Quiz title",
  "intro": "Short explanation",
  "start_label": "Start quiz",
  "result_title": "Your matches",
  "restart_label": "Retake quiz",
  "xp_per_answer": 100,
  "questions": [
    {
      "id": "unique-id",
      "prompt": "Question",
      "hint": "Optional hint",
      "options": [
        {
          "label": "Answer",
          "emoji": "single emoji",
          "scores": {"trait_name": 3, "another_trait": 1}
        }
      ]
    }
  ],
  "catalog": [
    {
      "brand": "Brand",
      "model": "Model",
      "subtitle": "Short positioning",
      "emoji": "single emoji",
      "description": "Why this item fits",
      "notes": ["note one", "note two", "note three"],
      "badges": ["badge one", "badge two"],
      "traits": {"trait_name": 5, "another_trait": 2}
    }
  ]
}

For a complete recommendation experience provide at least 5 meaningful questions, 4 options per question, 6 realistic catalog entries, and a shared trait vocabulary across every option and catalog item. Scores should normally be integers from 0 to 5.
The generated app automatically supplies progress, XP, a profile, match percentages, favorites, persistence and a retake flow.
Use concise, realistic business copy and a coherent brand palette. Never include scripts, HTML, iframe, remote assets, secrets, tracking IDs or executable content.
For unclear or risky requests return action=clarify and keep the existing spec unchanged.
For Persian set direction=rtl; otherwise ltr. Favor mobile-first UX, accessible contrast and genuinely useful flows over generic brochure sections.
"""


_BLOCKED_KEYS = {
    "script",
    "html",
    "iframe",
    "srcdoc",
    "javascript",
    "tracking_id",
    "secret",
    "token",
}
_SAFE_KEY = re.compile(r"^[a-zA-Z0-9_-]{1,60}$")


def initial_spec(name, business_type, description, language):
    spec = deepcopy(DEFAULT_SPEC)
    spec["app"].update(
        {
            "title": name,
            "language": language,
            "direction": "rtl" if language == "fa" else "ltr",
        }
    )
    spec["app"]["tagline"] = description[:180]
    spec["sections"][0]["title"] = name
    spec["sections"][0]["text"] = description[:260]
    spec["sections"][1]["title"] = {"de": "Unsere Leistungen", "fa": "خدمات ما"}.get(
        language, "Our services"
    )
    spec["business_type"] = business_type
    return sanitize_spec(spec)


def _extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("AI response did not contain JSON")
    return json.loads(text[start : end + 1])


def _clean_nested(value, depth=0):
    if depth > 5:
        return None
    if isinstance(value, str):
        return value[:2000]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return max(-10000, min(10000, value))
    if isinstance(value, list):
        cleaned = []
        for item in value[:50]:
            safe = _clean_nested(item, depth + 1)
            if safe is not None:
                cleaned.append(safe)
        return cleaned
    if isinstance(value, dict):
        cleaned = {}
        for raw_key, raw_value in list(value.items())[:40]:
            key = str(raw_key)[:60]
            key_lower = key.lower()
            if not _SAFE_KEY.match(key):
                continue
            if key_lower in _BLOCKED_KEYS or key_lower.startswith("on"):
                continue
            safe = _clean_nested(raw_value, depth + 1)
            if safe is not None:
                cleaned[key] = safe
        return cleaned
    return None


def sanitize_spec(spec):
    source = spec if isinstance(spec, dict) else {}
    result = deepcopy(DEFAULT_SPEC)
    app = source.get("app", {}) if isinstance(source.get("app", {}), dict) else {}
    brand = source.get("brand", {}) if isinstance(source.get("brand", {}), dict) else {}
    result["app"].update(
        {
            key: str(value)[:500]
            for key, value in app.items()
            if key in {"title", "tagline", "language", "direction"}
        }
    )
    result["brand"].update(
        {
            key: str(value)[:32]
            for key, value in brand.items()
            if key in {"primary", "accent", "background", "surface", "text"}
        }
    )
    result["features"] = [
        str(item)[:60]
        for item in source.get("features", [])[:30]
        if isinstance(item, (str, int))
    ]
    result["navigation"] = [
        str(item)[:60]
        for item in source.get("navigation", [])[:10]
        if isinstance(item, (str, int))
    ]

    allowed = {
        "hero",
        "services",
        "products",
        "booking",
        "gallery",
        "about",
        "contact",
        "testimonials",
        "faq",
        "loyalty",
        "form",
        "notice",
        "recommendation_quiz",
    }
    sections = []
    for raw in source.get("sections", [])[:24]:
        if not isinstance(raw, dict) or raw.get("type") not in allowed:
            continue
        clean = _clean_nested(raw)
        if isinstance(clean, dict):
            clean["type"] = raw["type"]
            sections.append(clean)
    result["sections"] = sections or deepcopy(DEFAULT_SPEC["sections"])
    return result


def _model_candidates():
    configured = [
        settings.OPENAI_MODEL,
        *getattr(settings, "OPENAI_FALLBACK_MODELS", []),
    ]
    candidates = []
    for model in configured:
        model = str(model or "").strip()
        if model and model not in candidates:
            candidates.append(model)
    return candidates


def _is_model_access_error(exc):
    message = str(exc).lower()
    status_code = getattr(exc, "status_code", None)
    return (
        status_code == 404
        or "model_not_found" in message
        or "must be verified" in message
        or "does not have access" in message
    )


def _create_response(client, context):
    candidates = _model_candidates()
    if not candidates:
        raise RuntimeError("No OpenAI model is configured")
    for index, model in enumerate(candidates):
        try:
            return client.responses.create(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=json.dumps(context, ensure_ascii=False),
            )
        except Exception as exc:
            if index == len(candidates) - 1 or not _is_model_access_error(exc):
                raise


def propose_change(project, user_message, history):
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    current = sanitize_spec(
        project.app_spec
        or initial_spec(
            project.name,
            project.business_type,
            project.description,
            project.language,
        )
    )
    context = {
        "project": {
            "name": project.name,
            "business_type": project.business_type,
            "description": project.description,
            "language": project.language,
        },
        "current_spec": current,
        "recent_messages": history[-10:],
        "request": user_message,
    }
    response = _create_response(client, context)
    payload = _extract_json(response.output_text)
    action = payload.get("action", "clarify")
    if action not in {"clarify", "apply"}:
        action = "clarify"
    return {
        "action": action,
        "message": str(payload.get("message") or "I need a little more detail.")[:4000],
        "feature_title": str(payload.get("feature_title") or "App update")[:220],
        "feature_description": str(
            payload.get("feature_description") or user_message
        )[:4000],
        "spec": sanitize_spec(payload.get("spec") or current),
    }
