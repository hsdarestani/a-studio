import json
import re

from django.conf import settings
from openai import OpenAI

from .ai import _is_model_access_error, _model_candidates
from .code_workspace import CodeWorkspaceError, apply_changes, deploy_workspace_preview, export_context


SYSTEM_PROMPT = """You are A+ Studio Code Agent V3. You edit a real static web application workspace.
Return ONLY valid JSON with this exact schema:
{
  "action": "apply" | "clarify",
  "message": "short user-facing answer in the project's language",
  "feature_title": "short title",
  "feature_description": "what changed and acceptance criteria",
  "files": [{"path":"relative/path.ext","content":"complete UTF-8 file contents"}],
  "deleted_files": []
}

Rules:
- You are editing executable client-side web code, not a declarative spec.
- Use maintainable HTML/CSS/JavaScript. You may create folders and modules, but index.html must always remain.
- Return complete contents for every changed file; never return patches or ellipses.
- Keep the change minimal: only include files that actually need modification.
- Never create .env files, secrets, tokens, server credentials, package manager lockfiles, binaries, shell scripts, PHP, executable files or hidden paths.
- Never embed credentials. Runtime backend configuration is provided through window.ASTUDIO_BACKEND when present.
- For managed authentication/database/storage, call only the supplied backend base URL. Do not invent API keys.
- Do not add analytics, trackers, advertising SDKs, crypto-mining, fingerprinting, hidden network calls, credential collection or data exfiltration.
- Do not use javascript: URLs or dynamically execute strings with eval/new Function.
- Prefer local assets/CSS. Remote public image URLs are allowed only when genuinely useful to the requested UI.
- Make responsive, accessible, polished interfaces. Preserve existing business content and working behavior unless the user asks to replace it.
- When the request is ambiguous enough that editing would likely be wrong, return action=clarify with no file changes.
"""


def _extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Code Agent response did not contain JSON")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Code Agent response must be an object")
    return value


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


def _safe_result(payload):
    action = str(payload.get("action") or "").lower()
    if action not in {"apply", "clarify"}:
        raise ValueError("Unsupported Code Agent action")
    files = payload.get("files") if isinstance(payload.get("files"), list) else []
    deleted_files = payload.get("deleted_files") if isinstance(payload.get("deleted_files"), list) else []
    if action == "clarify":
        files = []
        deleted_files = []
    clean_files = []
    for item in files[:40]:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")[:240]
        content = item.get("content")
        if path and isinstance(content, str):
            clean_files.append({"path": path, "content": content})
    return {
        "action": action,
        "message": str(payload.get("message") or "")[:4000],
        "feature_title": str(payload.get("feature_title") or "Code change")[:180],
        "feature_description": str(payload.get("feature_description") or "")[:2000],
        "files": clean_files,
        "deleted_files": [str(path)[:240] for path in deleted_files[:40] if path],
    }


def propose_code_change(project, user_message, history):
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    workspace = export_context(project)
    context = {
        "project": {
            "name": project.name,
            "business_type": project.business_type,
            "description": project.description,
            "language": project.language,
            "version": project.version,
            "backend": {
                "base_url": f"{settings.APP_PUBLIC_URL}/api/apps/{project.slug}",
                "features": project.backend_features or [],
            },
        },
        "request": str(user_message or "")[:12_000],
        "recent_history": list(history)[-12:],
        "workspace": workspace,
    }
    response = _create_response(OpenAI(api_key=settings.OPENAI_API_KEY), context)
    return _safe_result(_extract_json(response.output_text))


def apply_code_change(project, proposal):
    if proposal.get("action") != "apply":
        return {"changed": False}
    changes = apply_changes(project, proposal.get("files") or [], proposal.get("deleted_files") or [])
    root, checksum = deploy_workspace_preview(project)
    return {
        "changed": True,
        "root": root,
        "checksum": checksum,
        **changes,
    }
