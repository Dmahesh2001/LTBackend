# Deploying (free): Render + Neon + Upstash

```
Mobile app / Web app
        │  HTTPS
        ▼
api.loveandtails.com        Cloudflare DNS (record set to "DNS only")
        │
        ▼
Render web service          Django + gunicorn, free plan, Singapore
   ├── Neon                 PostgreSQL, free plan, Singapore
   └── Upstash              Redis, free plan, Singapore
```

Everything is on free plans; no credit card needed. All three services are in Singapore so they're close to each other (and to users in India).

## Free plan limits

| Service | Limit | What it means |
| --- | --- | --- |
| Render | Sleeps after 15 min without traffic; waking takes about 1 minute. 750 hours/month | The first request after a quiet period is slow. Fine for development and integration; move to a paid instance before launch |
| Neon | 1 GB storage, 100 compute-hours/month. Sleeps after 5 min without queries | Don't set up "keep-alive" pingers: keeping the database awake 24/7 uses up the monthly compute hours in about two weeks |
| Upstash | 500K commands/month, 250 MB | Rate limiting uses about 2–4 commands per API request, so roughly 125K+ requests/month |

## 1. Push the code to GitHub

Render deploys the `main` branch of `github.com/Dmahesh2001/LTBackend`. Every push to `main` redeploys automatically.

## 2. Create the database (Neon)

1. Sign up at [neon.com](https://neon.com).
2. Create a project: name `loveandtails`, region **AWS Asia Pacific (Singapore)**.
3. Open **Connect** and copy the connection string. Use the direct one, not the "pooled" one. It looks like:
   `postgresql://neondb_owner:...@ep-....ap-southeast-1.aws.neon.tech/neondb?sslmode=require`

## 3. Create Redis (Upstash)

1. Sign up at [upstash.com](https://upstash.com).
2. Create a Redis database, region **ap-southeast-1 (Singapore)**.
3. Copy the Redis URL that starts with `rediss://` (TLS). It looks like:
   `rediss://default:...@....upstash.io:6379`

## 4. Create the web service (Render)

1. Sign up at [render.com](https://render.com) with your GitHub account and give it access to the `LTBackend` repo.
2. **New → Blueprint**, pick the `LTBackend` repo. Render reads [render.yaml](render.yaml).
3. Fill in the values it asks for:

   | Variable | Value |
   | --- | --- |
   | `DATABASE_URL` | Neon connection string from step 2 |
   | `REDIS_URL` | Upstash `rediss://` URL from step 3 |
   | `CORS_ALLOWED_ORIGINS` | Web app origins, comma-separated, e.g. `https://loveandtails.com,https://www.loveandtails.com`. Add `http://localhost:3000` (your web dev server) to call this API while developing the web app |
   | `DJANGO_ADMIN_URL` | A non-obvious path ending in `/`, e.g. `manage-7f3k/` |

   Everything else (secret key, debug off, allowed hosts, proxy count) is already set in `render.yaml`.
4. Click **Apply**. The first build takes a few minutes. `build.sh` installs packages, collects static files and runs migrations.
5. Open `https://<your-service>.onrender.com/api/v1/health/` (the exact URL is on the service page). Expected:
   `{"status":"ok","database":"ok","cache":"ok"}`

## 5. Create your admin account

Render's free plan has no shell, so run this on your Mac, pointed at the Neon database:

```bash
source .venv/bin/activate
DATABASE_URL='<Neon connection string>' python manage.py createsuperuser
```

## 6. Use api.loveandtails.com

1. **Render:** service → **Settings → Custom Domains → Add** `api.loveandtails.com`.
2. **Cloudflare:** loveandtails.com → **DNS → Add record**:
   - Type `CNAME`, Name `api`, Target `<your-service>.onrender.com`
   - Proxy status: **DNS only** (grey cloud)
   - If there's an `AAAA` record for `api`, delete it (Render doesn't support IPv6).
3. Back in Render, click **Verify** and wait until the certificate shows as issued.
4. Check `https://api.loveandtails.com/api/v1/health/`.

**Why "DNS only":** Render already runs every service behind Cloudflare, so you still get DDoS protection and HTTPS. Turning on your own Cloudflare proxy adds a second hop, which changes how the app finds the real client IP (`NUM_PROXIES`) and would weaken the per-IP rate limits. This only affects the `api` record; the rest of loveandtails.com can stay proxied.

## 7. Connect the apps

| | |
| --- | --- |
| API base URL | `https://api.loveandtails.com/api/v1/` |
| Auth | `POST auth/token/` with email + password → send `Authorization: Bearer <access>` on each request; refresh with `POST auth/token/refresh/` |
| API docs | Log in at `https://api.loveandtails.com/<DJANGO_ADMIN_URL>`, then open `https://api.loveandtails.com/api/docs/` in the same browser |
| Web app | Its origin must be in `CORS_ALLOWED_ORIGINS` (Render → service → **Environment**) |
| Mobile apps | Nothing extra; CORS doesn't apply to native apps |

To open the docs to your whole team without an admin login (e.g. during integration), set `API_DOCS_PUBLIC=True` in Render → **Environment**.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| First request takes ~1 minute | The free instance was asleep |
| `400 Bad Request` on every URL | The domain isn't in `DJANGO_ALLOWED_HOSTS` (Render → **Environment**) |
| Health shows `"database": "unavailable"` | Wrong `DATABASE_URL`, or Neon's compute hours ran out for the month |
| Health shows `"cache": "unavailable"` | Wrong `REDIS_URL`, or Upstash's monthly commands ran out. The API keeps working, without rate limits |
| Web app gets CORS errors | Its exact origin (scheme + host + port) isn't in `CORS_ALLOWED_ORIGINS` |

Logs are in Render → service → **Logs**.
