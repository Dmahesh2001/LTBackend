# LTBackend

Backend API for the **Love and Tails** mobile and web applications.

**Stack:** Django 6.1 · Django REST Framework · PostgreSQL · Redis (cache, rate limits) · JWT auth (SimpleJWT) · OpenAPI/Swagger docs (drf-spectacular)

## Project layout

```
loveandtails/        Django project (settings, root URLs, WSGI/ASGI)
apps/
  core/              Shared utilities, health check
  users/             Custom User model (email login), auth + profile endpoints
  waitlist/          Waitlist signups + confirmation email
docker-compose.yml   Local PostgreSQL + Redis
.env.example         Environment variable template
```

## Getting started

### 1. Start PostgreSQL and Redis

With Docker:

```bash
docker compose up -d db redis
```

Or with Homebrew:

```bash
brew install postgresql@17 redis
brew services start postgresql@17
brew services start redis
createuser -s loveandtails
psql -d postgres -c "ALTER USER loveandtails WITH PASSWORD 'loveandtails';"
createdb -O loveandtails loveandtails
```

### 2. Set up Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then set DJANGO_SECRET_KEY
```

### 3. Migrate and run

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## API docs

| URL | Description |
| --- | --- |
| http://localhost:8000/api/docs/ | Swagger UI |
| http://localhost:8000/api/redoc/ | ReDoc |
| http://localhost:8000/api/schema/ | Raw OpenAPI 3 schema (YAML) |
| http://localhost:8000/admin/ | Django admin |

To try authenticated endpoints in Swagger UI: call `POST /api/v1/auth/token/`, copy the `access` token, click **Authorize**, and paste it.

The docs are public in development. In production (`DJANGO_DEBUG=False`) they are **staff only**: log in to the Django admin first, then open the docs in the same browser. Set `API_DOCS_PUBLIC=True` to open them up (e.g. on staging).

## Endpoints (v1)

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/health/` | – | Health check: database and Redis. `503` if the database is down; `200` + `"degraded"` if only Redis is down |
| GET | `/api/v1/health/live/` | – | Liveness only (no database/Redis), for the hosting platform's frequent health checks |
| POST | `/api/v1/auth/register/` | – | Create an account |
| POST | `/api/v1/auth/token/` | – | Log in, returns `access` + `refresh` tokens |
| POST | `/api/v1/auth/token/refresh/` | – | Exchange a refresh token for a new pair |
| POST | `/api/v1/auth/token/verify/` | – | Check whether a token is valid |
| POST | `/api/v1/auth/logout/` | – | Blacklist a refresh token |
| GET / PATCH | `/api/v1/users/me/` | Bearer | Current user's profile |
| POST | `/api/v1/waitlist/` | – | Join the waitlist (sends a confirmation email) |

Clients send `Authorization: Bearer <access token>`. Refresh tokens are rotated on use and the old one is blacklisted.

## Security

| Protection | Details |
| --- | --- |
| Rate limits | Every endpoint: 60/min per IP when logged out, 300/min per user when logged in. Login: 10/min per IP. Register: 10/hour per IP. Waitlist: 10/hour per IP. Health check: unlimited. Over the limit → `429` with a `Retry-After` header |
| Rate limit storage | Redis, shared by all server processes. If Redis is down, requests are allowed and the error is logged |
| Client IP | Taken from `X-Forwarded-For` using `NUM_PROXIES`, so clients can't fake their IP to dodge limits |
| JWT | Access 30 min, refresh 30 days. Refresh tokens rotate and can't be reused. Logout revokes the refresh token. Changing a password logs out every device. Deactivated or deleted users are rejected |
| Passwords | Django's validators (length, common passwords, similarity, all-numeric) |
| API docs | Staff only in production (`API_DOCS_PUBLIC`) |
| Responses | JSON only in production (no browsable HTML API) |
| CORS | Only `CORS_ALLOWED_ORIGINS`, only on `/api/`, no cookies (`CORS_ALLOW_CREDENTIALS`) |
| HTTPS (production) | HTTP → HTTPS redirect, HSTS, secure cookies |
| Headers | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin` |
| Hosts | Requests with a `Host` not in `DJANGO_ALLOWED_HOSTS` get `400` |
| Admin | Path configurable with `DJANGO_ADMIN_URL` |
| Logging | Warnings, errors and security events (`401`, `403`, `429`, bad hosts) go to stdout |

Before deploying, run `python manage.py check --deploy` with production settings.

### Waitlist

`POST /api/v1/waitlist/` with `{"email": "..."}`:

- `201` new signup; a confirmation email is sent if email sending is on
- `200` email already on the waitlist; no email is re-sent
- `400` invalid email
- `429` rate limited (10 requests/hour per IP)

Rate limit counters are kept in Redis, so the limit holds across all server processes. If Redis is unreachable, requests are allowed (and the error logged) instead of failing.

Signups are stored in Postgres (`waitlist_waitlistentry` table, emails lowercased) and can be viewed at `/admin/waitlist/waitlistentry/`.

Confirmation emails are **off until an email provider is configured** (`WAITLIST_CONFIRMATION_EMAILS` defaults to on only when `EMAIL_HOST` is set). Until then, and whenever sending fails, the signup is saved with `confirmation_sent_at` empty. To email them later: in the admin, filter **Confirmation sent at → Empty**, select all, and run **"Send waitlist confirmation email"**.

## Email

Emails are sent through `apps.core.emails.send_templated_email()`, which renders a `.txt` and `.html` template pair. HTML emails extend `emails/base.html`.

Without `EMAIL_HOST`, emails are printed to the `runserver` console. To send real email, set the SMTP settings below; any SMTP provider works (Amazon SES, SendGrid, Mailgun, Postmark, Resend...).

## Configuration

All settings come from environment variables (or `.env`). See [.env.example](.env.example).

| Variable | Default | Notes |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | – | Required |
| `DJANGO_DEBUG` | `False` | |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Add `10.0.2.2` for the Android emulator |
| `DATABASE_URL` | `postgres://loveandtails:loveandtails@localhost:5432/loveandtails` | |
| `REDIS_URL` | `redis://localhost:6379/0` | Use `rediss://` for TLS (most managed Redis) |
| `NUM_PROXIES` | unset | Number of proxies/load balancers in front of the app (usually `1` in production). Needed for correct per-IP rate limits; unset trusts the client's `X-Forwarded-For` header, which can be spoofed |
| `CORS_ALLOWED_ORIGINS` | – | Web app origins, e.g. `http://localhost:3000` |
| `CORS_ALLOW_CREDENTIALS` | `False` | Only needed if the web app switches to cookie-based auth |
| `API_DOCS_PUBLIC` | same as `DJANGO_DEBUG` | `False` = docs are staff only |
| `DJANGO_ADMIN_URL` | `admin/` | Use a non-obvious path in production, e.g. `manage-7f3k/` |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` | Production only. Redirect HTTP to HTTPS |
| `DJANGO_SECURE_HSTS_SECONDS` | `60` | Production only. Raise to `31536000` (1 year) once HTTPS is confirmed working |
| `LOG_LEVEL` | `INFO` | |
| `JWT_ACCESS_TOKEN_MINUTES` | `30` | |
| `JWT_REFRESH_TOKEN_DAYS` | `30` | |
| `DEFAULT_FROM_EMAIL` | `Love and Tails <noreply@localhost>` | Sender address; must be verified with your provider |
| `EMAIL_HOST` | – | SMTP host. Empty = print emails to console |
| `EMAIL_PORT` | `587` | |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | – | SMTP credentials |
| `EMAIL_USE_TLS` | `True` | |
| `EMAIL_TIMEOUT` | `10` | Seconds |
| `WAITLIST_CONFIRMATION_EMAILS` | on if `EMAIL_HOST` is set | Set `True` locally to preview the email in the console |

## Deployment

Hosted for free on Render (app), Neon (Postgres) and Upstash (Redis), at `https://api.loveandtails.com`. See [DEPLOY.md](DEPLOY.md); the service is defined in [render.yaml](render.yaml), and [build.sh](build.sh) installs packages, collects static files (served by WhiteNoise) and runs migrations on every deploy.

## Tests

```bash
python manage.py test
```

Tests use an in-memory cache, so they need Postgres running but never touch your local Redis.
