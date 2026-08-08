#!/usr/bin/env python3
import json
from pathlib import Path

EXPECTED_ID = "de.aplussolution.studio"
EXPECTED_NAME = "A+ Studio"

config_path = Path("capacitor.config.json")
package_path = Path("package.json")
www_path = Path("www/index.html")
app_path = Path("www/app.js")

for path in (config_path, package_path, www_path, app_path, Path("assets/icon.svg"), Path("assets/splash.svg")):
    if not path.exists():
        raise SystemExit(f"Missing store file: {path}")

config = json.loads(config_path.read_text(encoding="utf-8"))
if config.get("appId") != EXPECTED_ID:
    raise SystemExit(f"Unexpected appId: {config.get('appId')}")
if config.get("appName") != EXPECTED_NAME:
    raise SystemExit(f"Unexpected appName: {config.get('appName')}")
if config.get("webDir") != "www":
    raise SystemExit("Capacitor webDir must be local www")
if config.get("server", {}).get("url"):
    raise SystemExit("A+ Studio must not be a remote website wrapper")

app_js = app_path.read_text(encoding="utf-8")
required = [
    "https://studio.aplus-solution.de/api/mobile",
    "/account/delete/",
    "/projects/",
    "/store-submission/",
]
for marker in required:
    if marker not in app_js:
        raise SystemExit(f"Native client is missing required flow: {marker}")

print("A+ Studio store positioning check passed.")
