import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import SandboxRun
from .services.sandbox import apply_sandbox_callback, verify_signature


@csrf_exempt
@require_POST
def sandbox_callback(request, run_id):
    raw = request.body or b""
    supplied = request.headers.get("X-AStudio-Signature", "")
    if not verify_signature(raw, supplied):
        return JsonResponse({"error": "invalid signature"}, status=403)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "invalid json"}, status=400)
    run = get_object_or_404(SandboxRun.objects.select_related("project__organization", "requested_by"), pk=run_id)
    try:
        apply_sandbox_callback(run, payload)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "run_id": str(run.id)})
