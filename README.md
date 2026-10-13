# Vas3k Base

Community listings at [basa.club](https://basa.club), organized by
country, city and category. Members can publish listings, comment, vote, bookmark
items and subscribe to notifications. Authentication uses Vas3k Club and Telegram;
image uploads use the existing media service.

The backend is Django 6 with PostgreSQL. Django renders pages and handles forms;
Vite builds TypeScript behaviors and React islands. Background jobs use django-q2
with Redis, Telegram runs as a separate process, and Supercronic handles scheduled
maintenance.

## Local development

Requirements: Python 3.14, uv, Node.js 24, PostgreSQL and Redis.

Settings read environment variables directly. Export your local connection values
before running Django; `.env` files are not loaded automatically:

```sh
export POSTGRES_DB=vas3k_base
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_HOST=127.0.0.1
export REDIS_HOST=127.0.0.1
```

Create the PostgreSQL database, then install dependencies and apply migrations:

```sh
uv sync --frozen
npm ci --prefix frontend
uv run python manage.py migrate
```

Run these processes in separate terminals:

```sh
uv run python manage.py runserver 127.0.0.1:8000
```

```sh
npm run dev --prefix frontend
```

```sh
uv run python manage.py qcluster
```

Open http://127.0.0.1:8000. Django defaults to debug mode and loads frontend assets
from Vite on port 5173. Set `TELEGRAM_TOKEN` to a real bot token before starting
`uv run python bot/main.py`; the bot uses polling in development.

To use the built frontend locally:

```sh
npm run build --prefix frontend
VITE_DEV_MODE=false uv run python manage.py runserver
```

`docker-compose.yml` contains the development services and source mounts;
`docker-compose.production.yml` is a separate deployment configuration.

## Project layout

| Path | Purpose |
| --- | --- |
| `vas3k_base/` | Django settings, URLs and middleware |
| `items/`, `categories/`, `geo/` | Listings and their organization |
| `authn/`, `users/`, `godmode/` | Authentication, profiles and moderation |
| `comments/`, `counters/`, `bookmarks/` | Discussions, ratings and saved items |
| `notifications/`, `bot/` | Subscriptions and Telegram delivery |
| `templates/` | Server-rendered pages and reusable widgets |
| `frontend/src/` | TypeScript behaviors and React islands |
| `frontend/static/` | CSS, images, fonts and generated bundles |
| `etc/` | nginx and cron configuration |
| `Makefile` | Production application startup |
| `.github/` | Build and deployment workflows |

Add small HTML interactions in `frontend/src/behaviors/` and attach them with
`data-behavior`. Use `frontend/src/islands/` for widgets that render their own UI:

```django
{% island "MarkdownEditor" name="description" value=form.description.value|default:"" %}
```

Island keyword arguments become JSON props, with names converted to camelCase. Widgets inside forms submit regular named inputs through Django. React is reserved for interactive widgets; page content and navigation stay in Django templates. Reusable TypeScript helpers belong in `frontend/src/lib/`. See `AGENTS.md` for contributor conventions.

`npm run build --prefix frontend` checks TypeScript and builds Vite assets into
`frontend/static/dist/`. Django reads `dist/.vite/manifest.json`; production nginx
serves the exported static files under `/static/`.

## Production

Deployment follows Vas3k Club: GitHub Actions builds an image, creates `.env` from
repository secrets, copies it and Compose to the host, then runs `pull` and `up -d`.
The Docker build installs locked Python dependencies and builds the frontend with
`npm ci` and `npm run build`.

`make docker-run-production` applies migrations, updates categories from
`common/data/categories.yaml`, collects static files and starts Gunicorn. A
category update reports problems and still lets the server start. Compose mounts
`frontend/static/` from the host at `/tmp/static` so nginx can serve the collected
files. Queue workers, Telegram and cron run separately. Only the web container
runs migrations, including on container restarts.

### Host setup

Use the existing Linux amd64 host with Docker Engine and Compose v2. Create
`/home/vas3k/basa.club` and give the SSH deployment user ownership and Docker
access. nginx needs permission to traverse the directory and read `frontend/static/`.

Reuse host PostgreSQL with database `vas3k_base` and role `vas3k`, which must have
migration permissions. Containers connect through `host.docker.internal`;
PostgreSQL must listen on the private Docker gateway address and allow the Docker
subnet in `pg_hba.conf` and the host firewall.

Install `etc/nginx/basa.club.conf` alongside Club's vhost. It uses the existing
`/home/vas3k/certs` certificate paths; the certificate must cover `basa.club`.

Base binds Django to `127.0.0.1:8824` and Telegram to `127.0.0.1:8826`. Redis is
private to the Compose project and persists its queue in a Docker volume. The
existing media service handles uploads. Production uses the normal Django settings
with environment values from `docker-compose.production.yml` and `.env`.

### GitHub Actions

`.github/workflows/deploy.yml` deploys pushes to `main` and supports manual runs.
It publishes `ghcr.io/vas3k/base` with `sha-COMMIT` and `latest` tags, using the same
metadata and registry-cache setup as Club. The uploaded `.env` selects the commit
image. GitHub's automatic `GITHUB_TOKEN` authenticates both image publishing and
the host's image pull.

With `DEBUG=false`, Django requires an explicit `SECRET_KEY` and refuses to start without it. Development keeps its local default. Production logs use `INFO`; development logs use `DEBUG`.

Configure repository secrets:

| Secret | Value |
| --- | --- |
| `PRODUCTION_SSH_HOST` | Deployment hostname |
| `PRODUCTION_SSH_USERNAME` | Deployment user |
| `PRODUCTION_SSH_KEY` | Private deployment key |
| `PRODUCTION_SSH_KNOWN_HOSTS` | Verified SSH known-hosts entry |
| `SECRET_KEY` | Django secret key |
| `POSTGRES_PASSWORD` | Database password |
| `TELEGRAM_TOKEN` | Base bot token |
| `TELEGRAM_ADMIN_CHAT_ID` | Optional admin chat |
| `TELEGRAM_BASE_CHAT_ID` | Optional public Base chat for new items |
| `CLUB_OPENID_CONFIG_SECRET` | Club OAuth secret |
| `CLUB_SERVICE_TOKEN` | Club service token |
| `MEDIA_UPLOAD_CODE` | Media service upload credential |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP credentials |
| `SENTRY_DSN` | Optional error reporting |

`.env.example` lists the generated environment values for reference. CI replaces
the host `.env` on each deployment. There are no separate release scripts,
production settings module, or deployment health checks.

Deployments restart services with a brief interruption. Keep migrations compatible
with existing application and background processes, and back up the database before
releases. A failed startup or migration requires inspecting container logs; CI does
not wait for application readiness.

## Maintenance

Run management commands with `uv run python manage.py` locally. In production:

```sh
cd /home/vas3k/basa.club
docker compose -f docker-compose.production.yml exec app python manage.py createsuperuser
```

Useful commands include `recalculate_counters`, `update_search_index`,
`delete_expired_codes` and `clearsessions`. The latter three run on the schedules
in `etc/crontab`. Rating rules live in `counters/`.
