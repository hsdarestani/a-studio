import base64
import ipaddress
import json
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings


MAX_SOURCE_BYTES = 750_000
MAX_CONTEXT_CHARS = 32_000
GITHUB_FILES = (
    "README.md",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "composer.json",
    "Dockerfile",
    "vite.config.js",
    "vite.config.ts",
    "next.config.js",
    "next.config.mjs",
)


class SourceImportError(ValueError):
    pass


def _public_host(hostname):
    if not hostname:
        raise SourceImportError("The source URL needs a valid hostname.")
    lowered = hostname.rstrip(".").lower()
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".local"):
        raise SourceImportError("Local network URLs cannot be imported.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None)}
    except socket.gaierror as exc:
        raise SourceImportError("The source hostname could not be resolved.") from exc
    if not addresses:
        raise SourceImportError("The source hostname could not be resolved.")
    for raw in addresses:
        try:
            address = ipaddress.ip_address(raw.split("%", 1)[0])
        except ValueError as exc:
            raise SourceImportError("The source resolved to an invalid address.") from exc
        if not address.is_global:
            raise SourceImportError("Private, loopback and reserved network targets cannot be imported.")
    return lowered


def normalize_source_url(raw_url, source_type):
    raw_url = (raw_url or "").strip()
    if source_type == "prompt":
        return ""
    if not raw_url:
        raise SourceImportError("A source URL is required for this import mode.")
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise SourceImportError("Use a normal http(s) URL without embedded credentials.")
    if source_type == "github":
        if parsed.hostname.lower() != "github.com":
            raise SourceImportError("GitHub imports must use a github.com repository URL.")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise SourceImportError("Use a complete GitHub repository URL.")
        owner = parts[0]
        repo = re.sub(r"\.git$", "", parts[1], flags=re.I)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo):
            raise SourceImportError("The GitHub repository URL is invalid.")
        return f"https://github.com/{owner}/{repo}"
    _public_host(parsed.hostname)
    return raw_url


def _github_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "APlus-Studio-Importer/2",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


def _github_json(url):
    response = requests.get(url, headers=_github_headers(), timeout=(5, 15))
    if response.status_code == 404:
        raise SourceImportError("The GitHub repository was not found or is not accessible with the configured credentials.")
    response.raise_for_status()
    return response.json()


def _github_file(owner, repo, path, ref):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    response = requests.get(url, headers=_github_headers(), params={"ref": ref}, timeout=(5, 15))
    if response.status_code == 404:
        return ""
    response.raise_for_status()
    payload = response.json()
    if payload.get("encoding") != "base64" or not payload.get("content"):
        return ""
    try:
        decoded = base64.b64decode(payload["content"]).decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        return ""
    return decoded[:12_000]


def import_github_context(source_url):
    parsed = urlparse(normalize_source_url(source_url, "github"))
    owner, repo = [part for part in parsed.path.split("/") if part][:2]
    info = _github_json(f"https://api.github.com/repos/{owner}/{repo}")
    default_branch = info.get("default_branch") or "main"
    selected_files = {}
    for path in GITHUB_FILES:
        content = _github_file(owner, repo, path, default_branch)
        if content:
            selected_files[path] = content
        if sum(len(value) for value in selected_files.values()) >= MAX_CONTEXT_CHARS - 6000:
            break
    return {
        "source_type": "github",
        "source_url": f"https://github.com/{owner}/{repo}",
        "repository": {
            "full_name": info.get("full_name"),
            "description": info.get("description") or "",
            "default_branch": default_branch,
            "language": info.get("language") or "",
            "topics": info.get("topics") or [],
            "visibility": info.get("visibility") or ("private" if info.get("private") else "public"),
        },
        "files": selected_files,
    }


class _PageExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.headings = []
        self.text = []
        self._tag = ""
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        self._tag = tag.lower()
        if self._tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if self._tag == "meta":
            values = {str(k).lower(): str(v or "") for k, v in attrs}
            key = values.get("name", "").lower() or values.get("property", "").lower()
            if key in {"description", "og:description"} and not self.description:
                self.description = values.get("content", "")[:1200]

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        self._tag = ""

    def handle_data(self, data):
        if self._skip_depth:
            return
        clean = re.sub(r"\s+", " ", data or "").strip()
        if len(clean) < 2:
            return
        if self._tag == "title" and not self.title:
            self.title = clean[:500]
        elif self._tag in {"h1", "h2", "h3"} and len(self.headings) < 40:
            self.headings.append(clean[:500])
        elif len(" ".join(self.text)) < 16_000:
            self.text.append(clean[:1200])


def _safe_get(url):
    current = normalize_source_url(url, "url")
    for _ in range(4):
        parsed = urlparse(current)
        _public_host(parsed.hostname)
        response = requests.get(
            current,
            headers={"User-Agent": "APlus-Studio-Importer/2", "Accept": "text/html,application/xhtml+xml"},
            timeout=(5, 15),
            allow_redirects=False,
            stream=True,
        )
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            if not location:
                raise SourceImportError("The source returned an invalid redirect.")
            current = urljoin(current, location)
            normalize_source_url(current, "url")
            continue
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise SourceImportError("Build-from-URL currently accepts HTML websites only.")
        chunks = []
        size = 0
        for chunk in response.iter_content(chunk_size=16_384):
            if not chunk:
                continue
            size += len(chunk)
            if size > MAX_SOURCE_BYTES:
                raise SourceImportError("The source page is too large to import safely.")
            chunks.append(chunk)
        encoding = response.encoding or "utf-8"
        return current, b"".join(chunks).decode(encoding, errors="replace")
    raise SourceImportError("The source redirected too many times.")


def import_website_context(source_url):
    final_url, body = _safe_get(source_url)
    parser = _PageExtractor()
    parser.feed(body)
    return {
        "source_type": "url",
        "source_url": final_url,
        "title": parser.title,
        "description": parser.description,
        "headings": parser.headings[:30],
        "page_text": "\n".join(parser.text)[:18_000],
    }


def import_source_context(project):
    if project.source_type == "prompt":
        return {"source_type": "prompt"}
    if project.source_type == "github":
        return import_github_context(project.source_url)
    if project.source_type == "url":
        return import_website_context(project.source_url)
    raise SourceImportError("Unsupported project source type.")


def context_for_prompt(metadata):
    if not metadata or metadata.get("source_type") == "prompt":
        return ""
    serialized = json.dumps(metadata, ensure_ascii=False)
    return serialized[:MAX_CONTEXT_CHARS]
