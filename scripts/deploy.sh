#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/a-studio
RELEASE_DIR="$APP_DIR/releases/${GITHUB_SHA:-manual}"
CURRENT_DIR="$APP_DIR/current"

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
OPENAI_MODEL=gpt-5-mini
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
ENV
fi

python3 - "$ENV_FILE" "${OPENAI_API_KEY_B64:-}" "${EMAIL_PASSWORD_B64:-}" "${GITHUB_TOKEN_B64:-}" <<'PY'
import base64
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
encoded = {
    "OPENAI_API_KEY": sys.argv[2],
    "EMAIL_HOST_PASSWORD": sys.argv[3],
    "GITHUB_TOKEN": sys.argv[4],
}
defaults = {
    "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
    "EMAIL_HOST": "smtp.strato.de",
    "EMAIL_PORT": "465",
    "EMAIL_USE_SSL": "1",
    "EMAIL_USE_TLS": "0",
    "EMAIL_HOST_USER": "app@aplus-solution.de",
    "DEFAULT_FROM_EMAIL": "A+ Studio <app@aplus-solution.de>",
    "SERVER_EMAIL": "A+ Studio <app@aplus-solution.de>",
    "BILLING_CONTACT_EMAIL": "app@aplus-solution.de",
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
for key, value in encoded.items():
    if value:
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

docker compose up -d --build --remove-orphans

docker image prune -f >/dev/null 2>&1 || true

for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1/health/ >/dev/null; then
    echo "A+ Studio is healthy"
    exit 0
  fi
  sleep 5
done

echo "Deployment health check failed"
docker compose ps
docker compose logs --tail=150 web caddy
exit 1
