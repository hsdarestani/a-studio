#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "iOS builds require the Publisher macOS agent." >&2
  exit 2
fi

XCODE_VERSION="$(xcodebuild -version | awk '/Xcode/{print $2}' | head -n1)"
XCODE_MAJOR="${XCODE_VERSION%%.*}"
if [ -z "$XCODE_MAJOR" ] || [ "$XCODE_MAJOR" -lt 26 ]; then
  echo "App Store uploads require Xcode 26 or newer; found ${XCODE_VERSION:-unknown}." >&2
  exit 3
fi

python3 scripts/store_positioning_check.py

if [ ! -d node_modules ]; then
  if [ -f package-lock.json ]; then npm ci; else npm install; fi
fi

if [ ! -d ios ]; then
  npx cap add ios
fi

# The shared local UI also powers the Android companion. Prepare an iOS-only
# copy before `cap sync` so the App Store bundle does not mention competing
# distribution platforms, then restore the shared source immediately.
IOS_APP_JS="$ROOT/www/app.js"
IOS_APP_JS_BACKUP="$ROOT/www/.app.js.publisher-ios-backup"
restore_ios_web() {
  if [ -f "$IOS_APP_JS_BACKUP" ]; then
    mv "$IOS_APP_JS_BACKUP" "$IOS_APP_JS"
  fi
}
trap restore_ios_web EXIT
mv "$IOS_APP_JS" "$IOS_APP_JS_BACKUP"
cp "$IOS_APP_JS_BACKUP" "$IOS_APP_JS"
python3 - "$IOS_APP_JS" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

# Distribution status is read-only in the companion client. On iOS, show an
# Apple-only label even if a backend project also has another-platform status.
text = text.replace(
    'item.platform === "both" ? "Apple + Google" : item.platform === "ios" ? "Apple App Store" : "Google Play"',
    '"Apple App Store"',
)
path.write_text(text, encoding="utf-8")

for candidate in (Path("www/index.html"), Path("www/app.js"), Path("www/app.css")):
    payload = candidate.read_text(encoding="utf-8").lower()
    for forbidden in ("google", "android", "play store"):
        if forbidden in payload:
            raise SystemExit(
                f"iOS native web bundle still contains forbidden third-party platform reference {forbidden!r} in {candidate}"
            )

print("iOS native web bundle sanitized for App Store review.")
PY

npx cap sync ios
restore_ios_web
trap - EXIT

# A+ Studio's canonical store icon is assets/appicon.png. Capacitor Assets looks
# for assets/icon.*; temporarily expose the canonical PNG as icon.png and hide
# the legacy SVG so the generated native AppIcon set uses the committed artwork.
APPICON_SOURCE="$ROOT/assets/appicon.png"
ICON_PNG="$ROOT/assets/icon.png"
ICON_SVG="$ROOT/assets/icon.svg"
ICON_SVG_BACKUP="$ROOT/assets/.icon.svg.publisher-backup"
restore_icon_sources() {
  rm -f "$ICON_PNG"
  if [ -f "$ICON_SVG_BACKUP" ]; then
    mv "$ICON_SVG_BACKUP" "$ICON_SVG"
  fi
}
trap restore_icon_sources EXIT
if [ ! -f "$APPICON_SOURCE" ]; then
  echo "Canonical iOS icon is missing: $APPICON_SOURCE" >&2
  exit 4
fi
if [ -f "$ICON_SVG" ]; then
  mv "$ICON_SVG" "$ICON_SVG_BACKUP"
fi
cp "$APPICON_SOURCE" "$ICON_PNG"

npx @capacitor/assets generate --ios \
  --iconBackgroundColor '#0b0c0f' \
  --iconBackgroundColorDark '#0b0c0f' \
  --splashBackgroundColor '#0b0c0f' \
  --splashBackgroundColorDark '#0b0c0f' \
  --logoSplashScale 0.34

restore_icon_sources
trap - EXIT

APPICON_SET="$ROOT/ios/App/App/Assets.xcassets/AppIcon.appiconset"
if [ ! -d "$APPICON_SET" ] || [ ! -f "$APPICON_SET/Contents.json" ]; then
  echo "iOS AppIcon asset catalog was not generated." >&2
  exit 5
fi

PRIVACY_MANIFEST="$ROOT/ios/App/App/PrivacyInfo.xcprivacy"
cat > "$PRIVACY_MANIFEST" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>NSPrivacyTracking</key><false/>
  <key>NSPrivacyTrackingDomains</key><array/>
  <key>NSPrivacyCollectedDataTypes</key><array/>
  <key>NSPrivacyAccessedAPITypes</key><array/>
</dict></plist>
PLIST

mkdir -p artifacts build/ios
ARCHIVE="$ROOT/build/ios/AStudio.xcarchive"
EXPORT_DIR="$ROOT/build/ios/export"
VERSION="${APP_VERSION_NAME:-${APP_VERSION:-1.0.0}}"
# Build 3 was rejected on 2026-08-15. Default the next publisher build to 4;
# CI/release automation can always override with APP_BUILD_NUMBER/BUILD_NUMBER.
BUILD="${APP_BUILD_NUMBER:-${BUILD_NUMBER:-4}}"
TEAM_ID="${APPLE_TEAM_ID:-${IOS_TEAM_ID:-}}"
AUTH_KEY_PATH="${APPLE_AUTH_KEY_PATH:-${APPLE_API_KEY_PATH:-}}"
SIGNING_STYLE="${IOS_SIGNING_STYLE:-Automatic}"
PROFILE_SPECIFIER="${IOS_PROVISIONING_PROFILE_SPECIFIER:-}"
CODE_SIGN_IDENTITY="${IOS_CODE_SIGN_IDENTITY:-Apple Distribution}"
SIGNING_KEYCHAIN="${IOS_SIGNING_KEYCHAIN:-}"
BUNDLE_ID="${IOS_BUNDLE_ID:-de.aplussolution.studio}"

if [ -d ios/App/App.xcworkspace ]; then
  XCODE_CONTAINER=(-workspace ios/App/App.xcworkspace)
elif [ -d ios/App/App.xcodeproj ]; then
  XCODE_CONTAINER=(-project ios/App/App.xcodeproj)
else
  echo "No generated iOS Xcode project exists after cap sync." >&2
  exit 6
fi

XCODE_ARGS=(
  "${XCODE_CONTAINER[@]}"
  -scheme App
  -configuration Release
  -destination generic/platform=iOS
  -archivePath "$ARCHIVE"
  MARKETING_VERSION="$VERSION"
  CURRENT_PROJECT_VERSION="$BUILD"
  CODE_SIGN_STYLE="$SIGNING_STYLE"
  TARGETED_DEVICE_FAMILY=1
  PRODUCT_BUNDLE_IDENTIFIER="$BUNDLE_ID"
  INFOPLIST_KEY_ITSAppUsesNonExemptEncryption=NO
)

if [ -n "$TEAM_ID" ]; then
  XCODE_ARGS+=(DEVELOPMENT_TEAM="$TEAM_ID")
fi

if [ "$SIGNING_STYLE" = "Manual" ]; then
  if [ -z "$PROFILE_SPECIFIER" ] || [ -z "$SIGNING_KEYCHAIN" ]; then
    echo "Manual iOS signing requires Publisher provisioning profile and keychain." >&2
    exit 7
  fi
  XCODE_ARGS+=(
    CODE_SIGN_IDENTITY="$CODE_SIGN_IDENTITY"
    PROVISIONING_PROFILE_SPECIFIER="$PROFILE_SPECIFIER"
    "OTHER_CODE_SIGN_FLAGS=--keychain $SIGNING_KEYCHAIN"
  )
elif [ -n "$AUTH_KEY_PATH" ] && [ -n "${APPLE_KEY_ID:-}" ] && [ -n "${APPLE_ISSUER_ID:-}" ]; then
  XCODE_ARGS+=(
    -allowProvisioningUpdates
    -authenticationKeyPath "$AUTH_KEY_PATH"
    -authenticationKeyID "$APPLE_KEY_ID"
    -authenticationKeyIssuerID "$APPLE_ISSUER_ID"
  )
fi

xcodebuild "${XCODE_ARGS[@]}" clean archive

EXPORT_PLIST="$ROOT/build/ios/ExportOptions.plist"
TEAM_LINE=""
if [ -n "$TEAM_ID" ]; then
  TEAM_LINE="<key>teamID</key><string>${TEAM_ID}</string>"
fi

if [ "$SIGNING_STYLE" = "Manual" ]; then
  cat > "$EXPORT_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>method</key><string>app-store-connect</string>
<key>signingStyle</key><string>manual</string>
<key>signingCertificate</key><string>${CODE_SIGN_IDENTITY}</string>
<key>provisioningProfiles</key><dict>
  <key>${BUNDLE_ID}</key><string>${PROFILE_SPECIFIER}</string>
</dict>
<key>stripSwiftSymbols</key><true/>
<key>uploadSymbols</key><true/>
${TEAM_LINE}
</dict></plist>
PLIST
else
  cat > "$EXPORT_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>method</key><string>app-store-connect</string>
<key>signingStyle</key><string>automatic</string>
<key>stripSwiftSymbols</key><true/>
<key>uploadSymbols</key><true/>
${TEAM_LINE}
</dict></plist>
PLIST
fi

rm -rf "$EXPORT_DIR"
EXPORT_ARGS=(
  -exportArchive
  -archivePath "$ARCHIVE"
  -exportPath "$EXPORT_DIR"
  -exportOptionsPlist "$EXPORT_PLIST"
)
if [ -n "$AUTH_KEY_PATH" ] && [ -n "${APPLE_KEY_ID:-}" ] && [ -n "${APPLE_ISSUER_ID:-}" ]; then
  EXPORT_ARGS+=(
    -allowProvisioningUpdates
    -authenticationKeyPath "$AUTH_KEY_PATH"
    -authenticationKeyID "$APPLE_KEY_ID"
    -authenticationKeyIssuerID "$APPLE_ISSUER_ID"
  )
fi
xcodebuild "${EXPORT_ARGS[@]}"

IPA="$(find "$EXPORT_DIR" -name '*.ipa' -type f | head -n 1)"
if [ -z "$IPA" ]; then
  echo "No IPA was produced." >&2
  exit 8
fi
cp "$IPA" artifacts/a-studio.ipa

echo "iOS artifact: $ROOT/artifacts/a-studio.ipa"
