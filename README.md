# Noshiro DB Backend

Noshiro DB Backend is the Django REST backend for an anime and galgame catalog site. It provides public catalog APIs, user library/social APIs, Bangumi data synchronization, avatar storage through MinIO, and staff-only sync operations.

## Status

The current backend is ready for frontend integration:

- User auth, profile, avatar, library, progress, tags, rating details, reviews, collections, follows, activities, and public profile APIs are implemented.
- Public index APIs for subject search/detail, sections, relations, and daily anime calendar are implemented.
- Sync APIs and commands support full sync, incremental sync, calendar sync, and single-subject resync.
- API curl documentation lives in `docs/api/`.
- Frontend integration guidance lives in `docs/frontend-integration.md`.

## Stack

- Python 3.11
- Django 5.2
- Django REST Framework
- PostgreSQL
- Celery / Celery Beat
- MinIO
- SimpleJWT

## Project Structure

```text
apps/
  core/    shared API response, pagination, exceptions, handlers
  index/   public catalog models, selectors, serializers, views
  users/   auth, profile, user library, social features
  sync/    Bangumi providers, sync services, Celery tasks, admin sync APIs
config/
  settings/ split Django settings
docs/
  api/ frontend-facing curl API docs
  frontend-integration.md
```

Main layering convention:

```text
api/views        HTTP boundary only
api/serializers  request validation and response shape
selectors        read/query logic
services         write/business/sync logic
tasks            Celery task wrappers
```

## Local Setup

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure `.env`. The project reads `.env` directly; there is intentionally no committed env example in this repo.

Run migrations:

```bash
./venv/bin/python manage.py migrate
```

Start the API server:

```bash
./venv/bin/python manage.py runserver 0.0.0.0:8008
```

Run checks:

```bash
./venv/bin/python manage.py check
./venv/bin/python manage.py makemigrations --check --dry-run
```

## Environment

Important environment variables:

```text
DJANGO_SECRET_KEY
DJANGO_DEBUG
DJANGO_ALLOWED_HOSTS

DATABASE_NAME
DATABASE_USER
DATABASE_PASSWORD
DATABASE_HOST
DATABASE_PORT

CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS
CSRF_TRUSTED_ORIGINS

JWT_REFRESH_COOKIE_SECURE
JWT_REFRESH_COOKIE_SAMESITE

MINIO_ENDPOINT
MINIO_ACCESS_KEY
MINIO_SECRET_KEY
MINIO_BUCKET
MINIO_PUBLIC_URL

BANGUMI_API_BASE_URL
BANGUMI_API_KEY
BANGUMI_USER_AGENT
BANGUMI_TIMEOUT

CELERY_BROKER_URL
CELERY_RESULT_BACKEND
```

Production notes:

- Set `DJANGO_DEBUG=False`.
- Set explicit `DJANGO_ALLOWED_HOSTS`.
- Set explicit `CORS_ALLOWED_ORIGINS`.
- Use `CORS_ALLOW_CREDENTIALS=True` when the frontend uses refresh-cookie auth.
- Keep refresh tokens in HttpOnly cookies, not localStorage.

## API Documentation

Start here:

```text
docs/api/README.md
```

Main groups:

- `docs/api/users-auth.md`
- `docs/api/users-profile.md`
- `docs/api/users-subjects.md`
- `docs/api/index.md`
- `docs/api/sync.md`

Frontend handoff:

```text
docs/frontend-integration.md
```

## Frontend Auth Summary

Login/register returns an access token:

```json
{
  "access": "access_token_here"
}
```

Authenticated requests use:

```http
Authorization: Bearer access_token_here
```

Refresh token is stored in an HttpOnly cookie named `noshiro_refresh`.
Frontend refresh requests must include credentials:

```js
await fetch(`${baseUrl}/api/users/token/refresh/`, {
  method: "POST",
  credentials: "include",
});
```

Use `GET /api/users/me/profile/` after login/refresh. It returns `is_staff`, which the frontend can use to hide admin-only sync controls.

## Core Frontend Flows

Search/list:

```text
GET /api/index/subjects/?keyword={query}&page=1&page_size=16
```

Subject detail:

```text
GET /api/index/subjects/{subject_id}/
GET /api/index/subjects/{subject_id}/episodes/
GET /api/index/subjects/{subject_id}/staff/
GET /api/index/subjects/{subject_id}/characters/
GET /api/index/subjects/{subject_id}/relations/
```

Authenticated subject context:

```text
GET /api/users/me/subjects/{subject_id}/context/
```

Daily broadcast calendar:

```text
GET /api/index/calendar/
```

## Sync

Full sync:

```bash
./venv/bin/python manage.py full_sync
```

Single subject resync:

```bash
./venv/bin/python manage.py sync_subject --uuid "$SUBJECT_ID"
./venv/bin/python manage.py sync_subject --bangumi-id 123
```

Incremental sync:

```bash
./venv/bin/python manage.py incremental_sync --status
./venv/bin/python manage.py incremental_sync --batch-size 10
./venv/bin/python manage.py incremental_sync --task incremental_subject --batch-size 10
```

Calendar sync:

```bash
./venv/bin/python manage.py sync_calendar
./venv/bin/python manage.py sync_calendar --skip-subject-details
```

## Celery

Run worker:

```bash
celery -A config worker -l info
```

Run beat:

```bash
celery -A config beat -l info
```

Default schedules:

```text
03:30 daily calendar sync
04:00 daily incremental sync
```

Relevant schedule env vars:

```text
SYNC_CALENDAR_CRON_HOUR
SYNC_CALENDAR_CRON_MINUTE
SYNC_INCREMENTAL_CRON_HOUR
SYNC_INCREMENTAL_CRON_MINUTE
SYNC_INCREMENTAL_SUBJECT_BATCH_SIZE
SYNC_INCREMENTAL_MAX_CONSECUTIVE_ERRORS
SYNC_INCREMENTAL_MAX_CONSECUTIVE_SKIPS
```

## Verification

Before handing changes to the frontend or deploying:

```bash
./venv/bin/python manage.py check
./venv/bin/python manage.py makemigrations --check --dry-run
```

Then run the key smoke tests in:

```text
docs/api/README.md
```

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE).
