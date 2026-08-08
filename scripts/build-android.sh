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

npx @capacitor/assets generate --android \
  --iconBackgroundColor '#0b0c0f' \
  --iconBackgroundColorDark '#0b0c0f' \
  --splashBackgroundColor '#0b0c0f' \
  --splashBackgroundColorDark '#0b0c0f' \
  --logoSplashScale 0.34

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
  ./gradlew --no-daemon clean bundleRelease
)

AAB="$(find android/app/build/outputs/bundle/release -name '*.aab' -type f | head -n 1)"
if [ -z "$AAB" ]; then
  echo "No release AAB was produced." >&2
  exit 4
fi
cp "$AAB" artifacts/a-studio-release.aab

echo "Android artifact: $ROOT/artifacts/a-studio-release.aab"
