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
DEFAULT_FROM_EMAIL=studio@aplus-solution.de
GITHUB_OWNER=hsdarestani
GITHUB_REPOSITORY_PREFIX=astudio-app-
ENV
fi

python3 - "$ENV_FILE" "${OPENAI_API_KEY_B64}" <<'PY'
import base64, pathlib, sys
path = pathlib.Path(sys.argv[1])
value = base64.b64decode(sys.argv[2]).decode()
lines = path.read_text().splitlines()
key = "OPENAI_API_KEY"
updated = False
for i, line in enumerate(lines):
    if line.startswith(key + "="):
        lines[i] = f"{key}={value}"
        updated = True
if not updated:
    lines.append(f"{key}={value}")
path.write_text("\n".join(lines) + "\n")
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
