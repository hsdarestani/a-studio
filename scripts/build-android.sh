#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 scripts/store_positioning_check.py

if [ ! -d node_modules ]; then
  if [ -f package-lock.json ]; then npm ci; else npm install; fi
fi

TMP_SIGNING_DIR=""
if [ ! -f android/gradlew ] && [ -d android ]; then
  if [ -f android/upload-keystore.jks ] || [ -f android/key.properties ]; then
    TMP_SIGNING_DIR="$(mktemp -d)"
    [ ! -f android/upload-keystore.jks ] || mv android/upload-keystore.jks "$TMP_SIGNING_DIR/"
    [ ! -f android/key.properties ] || mv android/key.properties "$TMP_SIGNING_DIR/"
  fi
  rmdir android 2>/dev/null || {
    echo "android/ exists but is not a generated Capacitor project." >&2
    exit 2
  }
fi

if [ ! -f android/gradlew ]; then
  npx cap add android
fi

if [ -n "$TMP_SIGNING_DIR" ]; then
  [ ! -f "$TMP_SIGNING_DIR/upload-keystore.jks" ] || mv "$TMP_SIGNING_DIR/upload-keystore.jks" android/upload-keystore.jks
  [ ! -f "$TMP_SIGNING_DIR/key.properties" ] || mv "$TMP_SIGNING_DIR/key.properties" android/key.properties
  rmdir "$TMP_SIGNING_DIR"
fi

npx cap sync android
python3 scripts/configure_android_release.py

# A+ Studio's canonical launcher/store icon is assets/appicon.png. Capacitor
# Assets looks for assets/icon.*; temporarily expose the canonical PNG as
# icon.png and hide the legacy SVG so Android mipmap/adaptive icons are always
# generated from the exact same artwork shown in Google Play.
APPICON_SOURCE="$ROOT/assets/appicon.png"
ICON_PNG="$ROOT/assets/icon.png"
ICON_SVG="$ROOT/assets/icon.svg"
ICON_SVG_BACKUP="$ROOT/assets/.icon.svg.publisher-android-backup"
restore_icon_sources() {
  rm -f "$ICON_PNG"
  if [ -f "$ICON_SVG_BACKUP" ]; then
    mv "$ICON_SVG_BACKUP" "$ICON_SVG"
  fi
}
trap restore_icon_sources EXIT
if [ ! -f "$APPICON_SOURCE" ]; then
  echo "Canonical Android icon is missing: $APPICON_SOURCE" >&2
  exit 4
fi
if [ -f "$ICON_SVG" ]; then
  mv "$ICON_SVG" "$ICON_SVG_BACKUP"
fi
cp "$APPICON_SOURCE" "$ICON_PNG"

npx @capacitor/assets generate --android \
  --iconBackgroundColor '#0b0c0f' \
  --iconBackgroundColorDark '#0b0c0f' \
  --splashBackgroundColor '#0b0c0f' \
  --splashBackgroundColorDark '#0b0c0f' \
  --logoSplashScale 0.34

restore_icon_sources
trap - EXIT

mkdir -p artifacts

SIGNING_READY=0
if [ -n "${ANDROID_KEYSTORE_PATH:-}" ] && [ -f "${ANDROID_KEYSTORE_PATH}" ] && \
   [ -n "${ANDROID_KEYSTORE_PASSWORD:-}" ] && [ -n "${ANDROID_KEY_ALIAS:-}" ] && \
   [ -n "${ANDROID_KEY_PASSWORD:-}" ]; then
  export ASTUDIO_KEYSTORE_FILE="$ANDROID_KEYSTORE_PATH"
  SIGNING_READY=1
elif [ -n "${ANDROID_KEYSTORE_BASE64:-}" ] && \
     [ -n "${ANDROID_KEYSTORE_PASSWORD:-}" ] && \
     [ -n "${ANDROID_KEY_ALIAS:-}" ] && \
     [ -n "${ANDROID_KEY_PASSWORD:-}" ]; then
  printf '%s' "$ANDROID_KEYSTORE_BASE64" | base64 --decode > android/app/a-studio-release.jks
  export ASTUDIO_KEYSTORE_FILE="$ROOT/android/app/a-studio-release.jks"
  SIGNING_READY=1
fi

if [ "$SIGNING_READY" = "1" ]; then
  python3 scripts/configure_android_signing.py
elif [ "${REQUIRE_ANDROID_SIGNING:-0}" = "1" ]; then
  echo "Android signing credentials are required but missing." >&2
  exit 3
else
  echo "Signing credentials not supplied; building an unsigned verification bundle."
fi

(
  cd android
  for attempt in 1 2 3; do
    if ./gradlew --no-daemon clean bundleRelease; then
      exit 0
    fi
    if [ "$attempt" -ge 3 ]; then
      echo "Gradle release build failed after $attempt attempts." >&2
      exit 1
    fi
    echo "Gradle release build attempt $attempt failed; retrying after cleaning the wrapper download cache..." >&2
    rm -rf "$HOME/.gradle/wrapper/dists/gradle-8.14.3-all" 2>/dev/null || true
    sleep $((attempt * 8))
  done
)

AAB="$(find android/app/build/outputs/bundle/release -name '*.aab' -type f | head -n 1)"
if [ -z "$AAB" ]; then
  echo "No release AAB was produced." >&2
  exit 5
fi
cp "$AAB" artifacts/a-studio-release.aab

echo "Android artifact: $ROOT/artifacts/a-studio-release.aab"
