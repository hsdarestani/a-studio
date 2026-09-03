#!/usr/bin/env python3
import json
from pathlib import Path

EXPECTED_ID = "de.aplussolution.studio"
EXPECTED_NAME = "A+ Studio"

config_path = Path("capacitor.config.json")
package_path = Path("package.json")
www_path = Path("www/index.html")
app_path = Path("www/app.js")
store_profile_path = Path("docs/store-release.md")

for path in (
    config_path,
    package_path,
    www_path,
    app_path,
    Path("assets/icon.svg"),
    Path("assets/splash.svg"),
    store_profile_path,
):
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
    "KUNDENZUGANG",
    "Kundenprojekte",
    "Abstimmung",
    "Demo ansehen",
    "/mobile/privacy/",
    "/mobile/support/",
]
for marker in required:
    if marker not in app_js:
        raise SystemExit(f"Native customer-project client is missing required flow: {marker}")

# Guideline 2.5.2 regression guard: the App Store binary must remain a customer
# project coordination client, never an app builder, app previewer, software
# distribution client, or executable-code environment.
for forbidden in (
    "Preview öffnen",
    "Preview erstellen",
    "AI Builder",
    "Code Agent",
    "IDE-Vorschau",
    "Live veröffentlichen",
    "Kostenlos ausprobieren",
    "Start-Credits",
    "Store Submission",
    "Store-Einreichung",
    "Veröffentlichungsstatus",
    "/store-submission/",
    "/publish/",
    "/signup/",
    "Konto erstellen",
    'name="company_name"',
):
    if forbidden.lower() in app_js.lower():
        raise SystemExit(f"App Store customer-project client contains forbidden flow: {forbidden}")

store_profile = store_profile_path.read_text(encoding="utf-8")


def section_between(text: str, start: str, end: str) -> str:
    if start not in text or end not in text:
        raise SystemExit(f"Store metadata section missing: {start} / {end}")
    return text.split(start, 1)[1].split(end, 1)[0]


apple_description = section_between(
    store_profile,
    "**Apple description**",
    "**Google Play description**",
).lower()
google_description = section_between(
    store_profile,
    "**Google Play description**",
    "**Keywords (Apple)**",
).lower()

for forbidden in ("google play", "android"):
    if forbidden in apple_description:
        raise SystemExit(
            f"Apple App Store description must not reference third-party platform: {forbidden}"
        )

for forbidden in ("app store", "ios", "iphone", "ipad"):
    if forbidden in google_description:
        raise SystemExit(
            f"Google Play description must not reference Apple platform metadata: {forbidden}"
        )

for required_phrase in ("kundenbereich", "projektfortschritt", "projektteam"):
    if required_phrase not in apple_description:
        raise SystemExit(
            f"Apple description must clearly position the product as customer project coordination: {required_phrase}"
        )

for forbidden_phrase in (
    "softwareprojekte",
    "app-build",
    "preview",
    "programmcode",
    "store-einreich",
    "veröffentlichungsprozess",
    "code agent",
    "ide",
    "ai builder",
):
    if forbidden_phrase in apple_description:
        raise SystemExit(
            f"Apple description still contains software-builder positioning: {forbidden_phrase}"
        )

print("A+ Studio customer-project App Store positioning check passed.")
