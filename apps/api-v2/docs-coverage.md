# Coverage

What the Django app answers that this service does not yet (the community block,
mute and notification endpoints are already served and no longer listed). Counts come from
`apps/api/tests/snapshots/openapi.json` (126 operations on 92 paths) cross-checked
against the routers; the index app is fully ported, so it has no rows.

Paths omit the shared `/api/v1` prefix. `S` is a single query and a small payload,
`M` a few joins and validation, `L` multi-step logic or writes across tables.

## users — 35 paths

| path | methods | size |
|---|---|---|
| `/auth/sessions/code/` | POST | S |
| `/auth/sessions/refresh/` | POST | S |
| `/auth/social/github/start/` | GET | S |
| `/users/me/settings/` | GET,PATCH | S |
| `/users/me/tags/` | GET,POST | S |
| `/users/me/tags/{tag_id}/` | PATCH,DELETE | S |
| `/users/reviews/{review_id}/` | GET | S |
| `/users/{user_id}/collections/{collection_id}/` | GET | S |
| `/auth/password-resets/` | POST | M |
| `/auth/registrations/` | POST | M |
| `/auth/verification-codes/` | POST | M |
| `/users/entities/{entity_id}/reviews/` | GET | M |
| `/users/me/avatar/` | POST | M |
| `/users/me/collections/` | GET,POST | M |
| `/users/me/collections/{collection_id}/` | GET,PATCH,DELETE | M |
| `/users/me/collections/{collection_id}/items/{item_id}/` | PATCH,DELETE | M |
| `/users/me/library/entries/{entry_id}/` | GET,PATCH,DELETE | M |
| `/users/me/library/entries/{entry_id}/episodes/{episode_id}/progress/` | PUT,DELETE | M |
| `/users/me/library/entries/{entry_id}/rating-details/` | GET,PUT | M |
| `/users/me/library/entries/{entry_id}/releases/{release_id}/` | PUT,DELETE | M |
| `/users/me/library/entries/{entry_id}/reviews/` | GET,POST | M |
| `/users/me/library/entries/{entry_id}/tags/` | GET,PUT | M |
| `/users/me/profile/stats/` | GET | M |
| `/users/me/reviews/` | GET | M |
| `/users/me/reviews/{review_id}/` | GET,PATCH,DELETE | M |
| `/users/{user_id}/` | GET | M |
| `/users/{user_id}/collections/` | GET | M |
| `/users/{user_id}/collections/{collection_id}/items/` | GET | M |
| `/users/{user_id}/library/entries/` | GET | M |
| `/users/{user_id}/reviews/` | GET | M |
| `/auth/social/github/callback/` | GET | L |
| `/users/me/collections/{collection_id}/items/` | GET,POST,PUT | L |
| `/users/me/library/entries/` | GET,POST | L |
| `/users/me/library/entries/{entry_id}/episodes/progress/` | GET,PUT | L |

## community — 31 paths

| path | methods | size |
|---|---|---|
| `/community/activities/` | GET | M |
| `/community/comments/` | GET,POST | M |
| `/community/comments/{comment_id}/` | PATCH,DELETE | M |
| `/community/me/activities/` | GET | M |
| `/community/me/blocks/{target_user_id}/` | PUT,DELETE | M |
| `/community/me/bookmarks/` | GET | M |
| `/community/me/bookmarks/{target_type}/{target_id}/` | PUT,DELETE | M |
| `/community/me/feed/` | GET | M |
| `/community/me/mutes/{target_user_id}/` | PUT,DELETE | M |
| `/community/me/notifications/` | GET | M |
| `/community/me/reactions/{target_type}/{target_id}/{reaction_type}/` | PUT,DELETE | M |
| `/community/moderation/comments/{comment_id}/` | PATCH | M |
| `/community/moderation/posts/{post_id}/` | PATCH | M |
| `/community/moderation/reports/` | GET | M |
| `/community/posts/` | GET,POST | M |
| `/community/posts/{post_id}/` | GET,PATCH,DELETE | M |
| `/community/posts/{post_id}/comments/` | GET,POST | M |
| `/community/reports/` | POST | M |
| `/community/users/{user_id}/activities/` | GET | M |
| `/community/moderation/reports/{report_id}/` | PATCH | L |

## sync — 10 paths (staff only)

| path | methods | size |
|---|---|---|
| `/operations/import-jobs/{job_id}/` | GET | S |
| `/operations/sync/{campaign_id}/` | GET | S |
| `/operations/matching/candidates/` | GET | M |
| `/operations/sync/summary/` | GET | M |
| `/operations/sync/{campaign_id}/claims/` | GET | M |
| `/operations/sync/{campaign_id}/items/` | GET | M |
| `/operations/import-jobs/` | GET,POST | L |
| `/operations/matching/candidates/{candidate_id}/decide/` | POST | L |
| `/operations/sync/` | GET,POST | L |
| `/operations/sync/{campaign_id}/{action}/` | POST | L |

## Order

1. **community** — it touches only its own tables, with no Celery, object storage
   or third-party calls. Its writes share one shape (relation upsert plus an
   activity or notification fan-out) and its reads reuse the block and mute
   filters, so it can move endpoint by endpoint without touching the catalogue.
2. **users** — the library and collections carry the most rules (watch dates,
   cluster resolution, ownership) and the auth block needs email and captcha
   providers; both are better done once the community patterns exist.
3. **sync** — staff-only, depends on Celery and on the AI gateway; it moves with
   the ingestion pipeline, not before.

## Notes for the timeline block

The community timelines (`activities`, `me/activities`, `me/feed`, `me/notifications`)
use DRF's `CursorPagination` with `ordering = ("-created_at", "-id")` and a page
size of 16 (max 64):

- the envelope is `{next, previous, results}` — **no `count`**, unlike the
  paginated catalogue;
- a cursor is base64 of a query string with `o` (offset), `r` (reverse) and `p`
  (position), where the position is `str()` of the **first ordering field** —
  `created_at` for these endpoints — not a serialised timestamp and not a row id;
- the query is a keyset filter on `created_at` (`<` for the forward direction)
  with the offset handling rows that share a timestamp, and the page size is
  fetched plus one to know whether another page exists;
- the `next` link keeps `page_size` and replaces `cursor`.

`apps/api-v2/src/api/shared/cursor.py` reproduces the encoding; the endpoints
built on it still have to reproduce the filtering and the `+1` probe.
