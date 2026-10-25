# Running the replacement service

Everything below was exercised on the deployment host: the production dependency set
installs, the app starts, migrations apply and revert, and the read paths answer.
What has **not** run against a live dependency is the worker and the GitHub exchange —
`docs-cutover.md` lists both.

## Environment

Read from the process environment, or a `.env` beside the working directory.

| Variable | Needed for | Without it |
|---|---|---|
| `DATABASE_URL` | everything | the app starts but every request fails |
| `DJANGO_SECRET_KEY` | JWT signing and the OAuth state | tokens cannot be minted |
| `CELERY_BROKER_URL` | import jobs, sync campaigns | the row is written, nothing is dispatched |
| `RESEND_API_KEY` | verification mail | the code is written, no mail is sent (logged) |
| `EMAIL_FROM` | verification mail | the sender is `noreply@localhost` |
| `HCAPTCHA_ENABLED`, `HCAPTCHA_SECRET_KEY` | the code endpoint | the captcha is not enforced |
| `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET` | GitHub sign-in | the endpoints answer 503 |
| `GITHUB_OAUTH_REDIRECT_URI`, `GITHUB_OAUTH_SCOPES` | GitHub sign-in | redirect and scope fall back to empty / `read:user user:email` |
| `FRONTEND_SITE_URL` | the OAuth callback redirect | the browser lands on a relative path |

The first two are the only ones whose absence breaks the service; the rest degrade one
feature each, and each degradation is logged rather than silent.

## Start

```sh
uv sync --no-dev
uv run alembic upgrade head
uv run uvicorn api.main:app --host 127.0.0.1 --port 8010
```

`uv sync --no-dev` is not optional: a dependency (`httpx`) was missing from the
declared set and only showed up when the production set was installed alone.

## Health

The same two paths the old service exposes, with the same body and `Cache-Control`:

```sh
curl -s http://127.0.0.1:8010/health/live/    # {"status":"ok"} without touching the database
curl -s http://127.0.0.1:8010/health/ready/   # {"status":"ok"} after SELECT 1
```

Readiness answers 503 when the pool cannot answer. The old service also pings its cache
there; this one has no cache of its own, so that half is not reproduced.

## Migrations

Alembic owns the schema. `upgrade head` and `downgrade -1` were both run against the
production database; the migration that created the metric tables backfilled 551,018
and 697,636 rows.

## Rollback

The service only reads and writes the shared schema, and it never migrates down on its
own. Pointing the host back at Django is the rollback, provided the two migrations that
add tables stay applied — Django ignores tables it does not know.
