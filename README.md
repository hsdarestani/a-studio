# A+ Studio

A+ Studio is an AI-powered PWA software factory for A+ Solution GmbH. Customers describe the app they need, receive an isolated preview, refine it through chat, and publish only approved versions. Store publishing remains a managed A+ service.

## Included product capabilities

- Customer registration, organizations and team-ready membership model
- AI-generated initial PWA based on business context
- Conversational app changes using the OpenAI Responses API
- Safe declarative app specification instead of executing arbitrary model output
- Feature sizing, credit charging and a transaction ledger
- Background builds with Celery and Redis
- Preview/production separation, versioning, checksums and backups
- Installable PWA output with manifest, service worker and responsive UI
- Downloadable build and exported app specification
- Optional private GitHub repository per customer project
- Stripe-ready subscription checkout and webhook handling
- Store publishing request workflow for Android, iOS or both
- On-demand HTTPS for approved customer subdomains
- Docker-based production deployment through GitHub Actions
- PostgreSQL, Redis, Caddy, health checks and automatic HTTPS

## Architecture

```text
Browser
  -> Caddy / HTTPS
      -> Django + Gunicorn
          -> PostgreSQL
          -> Redis / Celery worker
          -> OpenAI Responses API
          -> Project generator
              -> /data/apps/preview/<slug>
              -> /data/apps/live/<slug>
          -> Optional GitHub customer repository
```

The AI never receives server secrets and does not execute arbitrary shell commands. It produces a validated declarative app specification. The deterministic generator then creates the PWA. This provides a safe production baseline while preserving the conversational experience.

## Production deployment

The repository expects these GitHub Actions secrets:

- `HOST`: server IP or SSH host
- `PASS`: root SSH password
- `OPENAIAPIKEY`: OpenAI API key

A push to `main` uploads the release, installs Docker when needed, creates a persistent environment file, starts PostgreSQL, Redis, Django, Celery and Caddy, then verifies both local and public health endpoints.

Production URL: `https://studio.aplus-solution.de`

## Additional credentials required for all commercial features

The three deployment secrets are enough to run the platform and AI builder. They are **not enough** to create private repositories in the customer's name or collect payments.

Configure these in `/opt/a-studio/shared/.env` when ready:

```env
GITHUB_TOKEN=...
GITHUB_OWNER=...
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
STRIPE_PRICE_STARTER=...
STRIPE_PRICE_BUSINESS=...
STRIPE_PRICE_PRO=...
```

For long-term GitHub provisioning, replace the PAT with a dedicated GitHub App and installation-token flow.

## DNS for customer subdomains

The main studio works with the single DNS record:

```text
studio.aplus-solution.de -> 5.75.193.49
```

To activate per-customer addresses such as `luna.studio.aplus-solution.de`, add this wildcard record at the DNS provider:

```text
*.studio.aplus-solution.de -> 5.75.193.49
```

Caddy asks the Django allow endpoint before issuing an on-demand certificate, and certificates are only allowed for live projects already registered in the database.

## Local development

```bash
cp .env.example .env
# set DEBUG=1 and a local SECRET_KEY
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

For the full stack:

```bash
docker compose up --build
```

## Security model

- No model-generated executable code is run on the host
- Preview and production directories are separate
- Production publishing copies only a completed preview build
- Previous production builds are retained under `/data/apps/backups`
- OpenAI and payment secrets are backend-only
- Repository provisioning is disabled until explicit GitHub credentials are configured
- Customer wildcard certificates require a database allow decision
- Django security headers, secure cookies and CSRF trusted origins are enabled in production

## Next infrastructure expansion

The codebase is ready for dedicated per-project containers and a true code-agent sandbox. That expansion requires a prebuilt toolchain image, restricted network egress, resource quotas, dependency caching, secret brokering, malware scanning and human review gates for high-risk changes. It should not be simulated by giving a language model direct access to the production server.
