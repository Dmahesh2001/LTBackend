# LTBackend

Backend API for the **Love and Tails** mobile and web applications.

**Stack:** Django 6.1 · Django REST Framework · PostgreSQL · JWT auth (SimpleJWT) · OpenAPI/Swagger docs (drf-spectacular)

## Project layout

```
loveandtails/        Django project (settings, root URLs, WSGI/ASGI)
apps/
  core/              Shared utilities, health check
  users/             Custom User model (email login), auth + profile endpoints
docker-compose.yml   Local PostgreSQL
.env.example         Environment variable template
```

## Getting started

### 1. Start PostgreSQL

With Docker:

```bash
docker compose up -d db
```

Or with Homebrew:

```bash
brew install postgresql@17
brew services start postgresql@17
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

## Endpoints (v1)

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/health/` | – | Health check (includes DB connectivity) |
| POST | `/api/v1/auth/register/` | – | Create an account |
| POST | `/api/v1/auth/token/` | – | Log in, returns `access` + `refresh` tokens |
| POST | `/api/v1/auth/token/refresh/` | – | Exchange a refresh token for a new pair |
| POST | `/api/v1/auth/token/verify/` | – | Check whether a token is valid |
| POST | `/api/v1/auth/logout/` | – | Blacklist a refresh token |
| GET / PATCH | `/api/v1/users/me/` | Bearer | Current user's profile |

Clients send `Authorization: Bearer <access token>`. Refresh tokens are rotated on use and the old one is blacklisted.

## Configuration

All settings come from environment variables (or `.env`). See [.env.example](.env.example).

| Variable | Default | Notes |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | – | Required |
| `DJANGO_DEBUG` | `False` | |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Add `10.0.2.2` for the Android emulator |
| `DATABASE_URL` | `postgres://loveandtails:loveandtails@localhost:5432/loveandtails` | |
| `CORS_ALLOWED_ORIGINS` | – | Web app origins, e.g. `http://localhost:3000` |
| `JWT_ACCESS_TOKEN_MINUTES` | `30` | |
| `JWT_REFRESH_TOKEN_DAYS` | `30` | |

## Tests

```bash
python manage.py test
```
