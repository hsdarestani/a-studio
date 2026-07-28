#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/a-studio
RELEASE_DIR="$APP_DIR/releases/${GITHUB_SHA:-manual}"
CURRENT_DIR="$APP_DIR/current"

show_diagnostics() {
  status=$?
  trap - ERR
  echo "Deployment failed with exit code $status near line ${BASH_LINENO[0]:-unknown}."
  if command -v docker >/dev/null 2>&1; then
    cd "$CURRENT_DIR" 2>/dev/null || true
    docker compose config >/tmp/a-studio-compose-config.log 2>&1 || cat /tmp/a-studio-compose-config.log || true
    docker compose ps -a || true
    docker compose logs --no-color --tail=120 db redis web worker caddy || true
    ss -ltnp 2>/dev/null | grep -E ':(22|80|443|8000)\b' || true
  fi
  exit "$status"
}
trap show_diagnostics ERR

mkdir -p "$RELEASE_DIR"
tar -xzf /tmp/a-studio-release.tar.gz -C "$RELEASE_DIR"

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

mkdir -p "$APP_DIR/shared"
ENV_FILE="$APP_DIR/shared/.env"
if [ ! -f "$ENV_FILE" ]; then
  DB_PASSWORD="$(openssl rand -hex 24)"
  SECRET_KEY="$(openssl rand -hex 48)"
  cat > "$ENV_FILE" <<ENV
DEBUG=0
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=studio.aplus-solution.de,.studio.aplus-solution.de,5.75.193.49,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://studio.aplus-solution.de
POSTGRES_DB=astudio
POSTGRES_USER=astudio
POSTGRES_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql://astudio:$DB_PASSWORD@db:5432/astudio
REDIS_URL=redis://redis:6379/0
OPENAI_MODEL=gpt-4.1-mini
OPENAI_FALLBACK_MODELS=gpt-4o-mini,gpt-4.1-nano
APP_PUBLIC_URL=https://studio.aplus-solution.de
APP_ROOT_DOMAIN=studio.aplus-solution.de
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.strato.de
EMAIL_PORT=465
EMAIL_USE_SSL=1
EMAIL_USE_TLS=0
EMAIL_HOST_USER=app@aplus-solution.de
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=A+ Studio <app@aplus-solution.de>
SERVER_EMAIL=A+ Studio <app@aplus-solution.de>
BILLING_CONTACT_EMAIL=app@aplus-solution.de
GITHUB_OWNER=hsdarestani
GITHUB_REPOSITORY_PREFIX=astudio-app-
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
APPLE_OAUTH_CLIENT_ID=
APPLE_OAUTH_KEY_ID=
APPLE_OAUTH_TEAM_ID=
APPLE_OAUTH_PRIVATE_KEY_B64=
ENV
fi

python3 - "$ENV_FILE" \
  "${OPENAI_API_KEY_B64:-}" "${EMAIL_PASSWORD_B64:-}" "${GITHUB_TOKEN_B64:-}" \
  "${GOOGLE_CLIENT_ID_B64:-}" "${GOOGLE_CLIENT_SECRET_B64:-}" \
  "${APPLE_CLIENT_ID_B64:-}" "${APPLE_KEY_ID_B64:-}" "${APPLE_TEAM_ID_B64:-}" "${APPLE_PRIVATE_KEY_B64:-}" <<'PY'
import base64
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
keys = [
    "OPENAI_API_KEY", "EMAIL_HOST_PASSWORD", "GITHUB_TOKEN",
    "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET",
    "APPLE_OAUTH_CLIENT_ID", "APPLE_OAUTH_KEY_ID", "APPLE_OAUTH_TEAM_ID", "APPLE_OAUTH_PRIVATE_KEY_B64",
]
encoded = dict(zip(keys, sys.argv[2:]))
defaults = {
    "OPENAI_MODEL": "gpt-4.1-mini",
    "OPENAI_FALLBACK_MODELS": "gpt-4o-mini,gpt-4.1-nano",
    "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
    "EMAIL_HOST": "smtp.strato.de",
    "EMAIL_PORT": "465",
    "EMAIL_USE_SSL": "1",
    "EMAIL_USE_TLS": "0",
    "EMAIL_HOST_USER": "app@aplus-solution.de",
    "DEFAULT_FROM_EMAIL": "A+ Studio <app@aplus-solution.de>",
    "SERVER_EMAIL": "A+ Studio <app@aplus-solution.de>",
    "BILLING_CONTACT_EMAIL": "app@aplus-solution.de",
    "GOOGLE_OAUTH_CLIENT_ID": "",
    "GOOGLE_OAUTH_CLIENT_SECRET": "",
    "APPLE_OAUTH_CLIENT_ID": "",
    "APPLE_OAUTH_KEY_ID": "",
    "APPLE_OAUTH_TEAM_ID": "",
    "APPLE_OAUTH_PRIVATE_KEY_B64": "",
}

lines = path.read_text().splitlines()
values = {}
order = []
for line in lines:
    if not line or line.lstrip().startswith("#") or "=" not in line:
        order.append((None, line))
        continue
    key, value = line.split("=", 1)
    values[key] = value
    order.append((key, None))

for key, value in defaults.items():
    values.setdefault(key, value)
if values.get("OPENAI_MODEL") in {"", "gpt-5-mini"}:
    values["OPENAI_MODEL"] = "gpt-4.1-mini"
for key, value in encoded.items():
    if value:
        # Keep the Apple .p8 key encoded so the dotenv file stays one-line-safe.
        if key == "APPLE_OAUTH_PRIVATE_KEY_B64":
            values[key] = value
        else:
            values[key] = base64.b64decode(value).decode()

written = set()
output = []
for key, raw in order:
    if key is None:
        output.append(raw)
    elif key not in written:
        output.append(f"{key}={values.get(key, '')}")
        written.add(key)
for key, value in values.items():
    if key not in written:
        output.append(f"{key}={value}")
path.write_text("\n".join(output) + "\n")
PY

ln -sfn "$ENV_FILE" "$RELEASE_DIR/.env"
ln -sfn "$RELEASE_DIR" "$CURRENT_DIR"
cd "$CURRENT_DIR"

docker compose config >/tmp/a-studio-compose-config.log
docker compose up -d --build --remove-orphans
docker image prune -f >/dev/null 2>&1 || true

for i in $(seq 1 30); do
  if docker compose exec -T web curl -fsS http://127.0.0.1:8000/health/ >/dev/null; then
    echo "A+ Studio application is healthy"
    exit 0
  fi
  sleep 5
done

echo "Deployment health check failed"
false
