# Backlog

## Now: Deploy (Render + Neon + Upstash, all free)

Step-by-step guide: [DEPLOY.md](DEPLOY.md).

- [x] Production setup in code: WhiteNoise for static files, `build.sh`, `render.yaml`, `.python-version`, lightweight health check for Render (verified locally in a Render-like setup, 2026-10-31)
- [ ] Push the code to `main` on GitHub
- [ ] Create the Neon database (Singapore) and copy its connection string
- [ ] Create the Upstash Redis database (Singapore) and copy its `rediss://` URL
- [ ] Render → New → Blueprint → fill in `DATABASE_URL`, `REDIS_URL`, `CORS_ALLOWED_ORIGINS`, `DJANGO_ADMIN_URL`
- [ ] Create the admin account from your Mac against Neon (`createsuperuser`)
- [ ] Add `api.loveandtails.com` in Render, and a `CNAME api` record in Cloudflare set to **DNS only**
- [ ] Check that per-IP rate limits work on the live server (fake `X-Forwarded-For` values must still get `429`)

**Done when:** `https://api.loveandtails.com/api/v1/health/` returns `{"status":"ok","database":"ok","cache":"ok"}`.

## Before launch

### 1. Send real emails (Resend)

**Why:** Waitlist confirmation emails are switched off. Signups are saved in Postgres, but nobody gets an email yet.

**Steps**
- [ ] Sign up at [resend.com](https://resend.com) (free: 3,000 emails/month, max 100/day)
- [ ] Domains → Add Domain `loveandtails.com` → add the DNS records (SPF, DKIM) in Cloudflare DNS → Verify
- [ ] API Keys → Create API Key ("Sending access")
- [ ] Add in Render → service → **Environment** (saving redeploys the app):
  ```
  DEFAULT_FROM_EMAIL=Love and Tails <hello@loveandtails.com>
  EMAIL_HOST=smtp.resend.com
  EMAIL_PORT=587
  EMAIL_HOST_USER=resend
  EMAIL_HOST_PASSWORD=re_your_api_key_here
  EMAIL_USE_TLS=True
  ```
  Setting `EMAIL_HOST` also turns on waitlist confirmation emails.
- [ ] Join the waitlist with your own email and confirm the email arrives (check spam too)
- [ ] Email everyone who signed up while sending was off: Admin → Waitlist entries → filter **Confirmation sent at → Empty** → select all → **"Send waitlist confirmation email"**. The free plan sends at most 100/day, so do this in batches of up to 100 per day.

**Done when:** a new signup receives the confirmation email, and no entries have an empty "Confirmation sent at".

### 2. Send emails in the background

**Why:** The email is sent while the signup request waits, which adds about a second with real SMTP. If sending fails, someone has to resend it by hand from the admin.

**Steps**
- [ ] Choose a task runner: Django's built-in Tasks framework (`django.tasks`) plus a worker backend such as the `django-tasks` package, or Celery + Redis (Redis is already set up, see item 3)
- [ ] Turn `send_waitlist_confirmation` (`apps/waitlist/emails.py`) into a background task with automatic retries
- [ ] Run the worker process in production alongside the web server (note: Render background workers aren't on the free plan)

**Done when:** the signup response no longer waits on the email, and failed sends retry automatically.

### 3. Shared cache (Redis) for rate limiting

**Status:** code done and verified locally (2026-10-31); production Redis is created during the deploy above.

**Why:** The 10-requests-per-hour limit on `POST /api/v1/waitlist/` was counted separately in each server process. With several gunicorn workers, the real limit became 10 × number of workers.

**Steps**
- [x] `pip install redis` and add it to `requirements.txt`
- [x] In settings, set `CACHES` to `django.core.cache.backends.redis.RedisCache` using a `REDIS_URL` env var
- [x] Local Redis (Homebrew service; also in `docker-compose.yml`)
- [x] If Redis is down, allow requests instead of failing; health check reports Redis status
- [x] Make the proxy count configurable (`NUM_PROXIES`) so clients can't dodge the limit with a fake `X-Forwarded-For` header
- [x] `NUM_PROXIES=2` for Render (its Cloudflare edge + its proxy), set in `render.yaml`
- [ ] Production Redis on Upstash with `REDIS_URL` set in Render (deploy step)
- [ ] Check `GET /api/v1/health/` on the server returns `"cache": "ok"`

**Done when:** in production, the 11th waitlist request from one IP within an hour gets `429`, regardless of which worker handles it.

### 4. Production security settings

**Why:** The API's security protections are built and tested (see "Security" in the README), but several of them depend on server settings.

**Steps**
- [x] `DJANGO_ALLOWED_HOSTS=api.loveandtails.com` and `API_DOCS_PUBLIC=False`, set in `render.yaml`
- [x] `check --deploy` with production settings: clean apart from `security.W021` (HSTS preload, optional) once an email provider is set (checked locally, 2026-10-31)
- [ ] `CORS_ALLOWED_ORIGINS` and a non-obvious `DJANGO_ADMIN_URL` (Render asks for both during the deploy)
- [ ] Before launch, remove `http://localhost:...` from `CORS_ALLOWED_ORIGINS`
- [ ] Once HTTPS on `api.loveandtails.com` is confirmed working, raise `DJANGO_SECURE_HSTS_SECONDS` to `31536000` (1 year)
- [ ] Run `python manage.py flushexpiredtokens` daily. Logout and token rotation add rows to the token blacklist tables, and this removes the expired ones. Render cron jobs aren't free; a scheduled GitHub Actions workflow with `DATABASE_URL` as a secret works for free

**Done when:** `/api/docs/` returns `401` when logged out on the live server, and expired tokens are cleaned up daily.

### 5. Move off free plans before launch

**Why:** Render's free instance sleeps after 15 minutes and takes about a minute to wake, which is too slow for real users (e.g. someone joining the waitlist).

**Steps**
- [ ] Upgrade the Render web service to a paid instance (no sleep)
- [ ] Check Neon and Upstash usage against their free limits, and upgrade if needed

## Later

- [ ] Admin login protection: lock out after repeated failed logins (`django-axes`) and/or two-factor auth for staff
- [ ] Bot protection on register and waitlist (Cloudflare Turnstile or hCaptcha) if spam signups show up
- [ ] Run `pip-audit` in CI to catch dependencies with known vulnerabilities (clean as of 2026-10-31)
