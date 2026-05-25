# Frontend Integration Guide

This document is the handoff guide for building the frontend against the Noshiro backend.

## API Base

Local development:

```text
http://127.0.0.1:8008
```

All responses use the same envelope:

```json
{
  "code": 0,
  "message": "",
  "data": {}
}
```

Paginated APIs put pagination inside `data`:

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

## Authentication

Login/register returns a short-lived access token:

```json
{
  "access": "access_token_here"
}
```

Send the access token on authenticated requests:

```http
Authorization: Bearer access_token_here
```

The refresh token is stored in an HttpOnly cookie named `noshiro_refresh`.
Browser refresh/logout requests must include credentials:

```js
await fetch(`${baseUrl}/api/users/token/refresh/`, {
  method: "POST",
  credentials: "include",
});
```

Frontend storage recommendation:

- Keep access token in app memory.
- Do not store refresh token in localStorage.
- On page reload, call refresh with `credentials: "include"` and recover a new access token.
- If refresh fails, treat the user as logged out.

## Current User

Use this after login or refresh:

```text
GET /api/users/me/profile/
```

Important fields:

```text
user_id
email
is_staff
is_superuser
nickname
avatar
theme_color
```

Use `is_staff` to show or hide admin-only sync controls. Backend sync APIs still enforce staff permission.

## Catalog Flow

Search/list page:

```text
GET /api/index/subjects/?keyword={query}&page=1&page_size=16
```

The list endpoint only returns primary site content:

```text
anime
galgame
```

Subject detail page:

```text
GET /api/index/subjects/{subject_id}/
```

Detail lookup accepts any subject UUID, including non-anime/non-galgame entries reached from relations.

Load heavy sections separately:

```text
GET /api/index/subjects/{subject_id}/episodes/?page=1&page_size=96
GET /api/index/subjects/{subject_id}/staff/?page=1&page_size=16
GET /api/index/subjects/{subject_id}/characters/?page=1&page_size=16
GET /api/index/subjects/{subject_id}/relations/
```

When switching a section page, refresh only that section.

## User Subject Context

On an authenticated anime/galgame detail page, load the user's private context:

```text
GET /api/users/me/subjects/{subject_id}/context/
```

This returns whether the subject is marked, plus user tags, reviews, rating details, and finished episode IDs.
Use subject UUID APIs for user actions where available, so the frontend does not need to expose `UserSubject.id` in the main detail workflow.

## Calendar

Daily broadcast calendar:

```text
GET /api/index/calendar/
```

Filter by weekday:

```text
GET /api/index/calendar/?weekday_en=Mon
```

Supported weekdays:

```text
Mon Tue Wed Thu Fri Sat Sun
```

The calendar is a current snapshot from Bangumi and is refreshed by sync.

## Admin Sync

Staff-only APIs:

```text
GET  /api/sync/incremental/status/
POST /api/sync/incremental/run/
POST /api/sync/calendar/run/
POST /api/sync/subjects/{subject_id}/resync/
```

Most sync APIs default to async Celery dispatch. For local debugging, pass:

```json
{
  "run_async": false
}
```

Do not expose sync controls to non-staff users.

## API Docs

Detailed curl examples live in:

```text
docs/api/README.md
```
