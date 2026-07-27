import base64
import json
from pathlib import Path
import requests
from django.conf import settings

API = "https://api.github.com"


def _headers():
    if not settings.GITHUB_TOKEN:
        raise RuntimeError("GitHub project provisioning is not configured. Add GITHUB_TOKEN or a GitHub App integration.")
    return {"Authorization": f"Bearer {settings.GITHUB_TOKEN}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def ensure_project_repository(project):
    if project.repo_name:
        return project.repo_url
    name = f"{settings.GITHUB_REPOSITORY_PREFIX}{project.slug}"[:100]
    owner = settings.GITHUB_OWNER
    payload = {"name": name, "description": f"Generated PWA for {project.name}", "private": True, "auto_init": True}
    endpoint = f"{API}/orgs/{owner}/repos" if _is_organization(owner) else f"{API}/user/repos"
    response = requests.post(endpoint, headers=_headers(), json=payload, timeout=30)
    if response.status_code not in {201, 422}:
        raise RuntimeError(f"GitHub repository creation failed: {response.status_code} {response.text[:500]}")
    if response.status_code == 422:
        response = requests.get(f"{API}/repos/{owner}/{name}", headers=_headers(), timeout=30)
    data = response.json()
    project.repo_name = name
    project.repo_url = data.get("html_url", f"https://github.com/{owner}/{name}")
    project.save(update_fields=["repo_name", "repo_url", "updated_at"])
    return project.repo_url


def _is_organization(owner):
    response = requests.get(f"{API}/users/{owner}", headers=_headers(), timeout=20)
    return response.ok and response.json().get("type") == "Organization"


def _put_file(repo, path, content, message):
    owner = settings.GITHUB_OWNER
    endpoint = f"{API}/repos/{owner}/{repo}/contents/{path}"
    existing = requests.get(endpoint, headers=_headers(), timeout=20)
    payload = {"message": message, "content": base64.b64encode(content.encode()).decode()}
    if existing.ok:
        payload["sha"] = existing.json()["sha"]
    response = requests.put(endpoint, headers=_headers(), json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"GitHub sync failed for {path}: {response.status_code} {response.text[:500]}")


def sync_project_repository(project, build_root):
    ensure_project_repository(project)
    _put_file(project.repo_name, "app-spec.json", json.dumps(project.app_spec, ensure_ascii=False, indent=2), f"Update app specification v{project.version}")
    _put_file(project.repo_name, "README.md", f"# {project.name}\n\nGenerated and managed by A+ Studio.\n\nLive: {project.live_url}\n", "Update project documentation")
    for path in Path(build_root).iterdir():
        if path.is_file():
            _put_file(project.repo_name, f"public/{path.name}", path.read_text(encoding="utf-8"), f"Build v{project.version}: {path.name}")
