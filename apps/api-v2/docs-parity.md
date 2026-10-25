# Parity

Every endpoint is compared with the Django service before traffic moves. The tool
is `scripts/parity.py`; it compares status codes, then the document structurally
(dict keys as sets, list order significant, numbers by value).

## Shadow runs

`parity.py` checks the paths it is given; `scripts/shadow.py` samples them. It
picks random public entities and also walks the catalogue, its filters and the
collections, runs everything through both services and reports how many
comparisons matched. Order-insensitive lists
are compared as sets; the links (`next`, `previous`) and `trace_id` are ignored.

```bash
DATABASE_URL=... uv run python -m scripts.shadow \
  --old http://127.0.0.1:8008 --new http://127.0.0.1:8010 --count 30
```

## Mutations

A write cannot be compared by sending the same request twice: the first call
changes the rows the second would act on. `scripts/state_parity.py` runs the
request against one service from a seed, snapshots the touched rows, restores the
seed and runs it against the other, then compares the responses and the snapshots.

```bash
uv run python -m scripts.state_parity --old ... --new ... \
  --setup "..." --snapshot "..." --cleanup "..." --method PUT --path ...
```

## Evidence log

| Date | Endpoint | Cases | Result |
|---|---|---|---|
| 2026-10-25 | `GET /api/v1/index/entities/{id}/metrics/` | 4 entities (one merged cluster of 3, three largest by metric count) | **OK, zero differences** |
| 2026-10-25 | same, unknown entity | 404 | **OK** — same `application/problem+json` envelope (`trace_id` ignored) |
| 2026-10-25 | `GET /api/v1/index/collections/` | 1 | **OK** |
| 2026-10-25 | `GET /api/v1/index/entities/{id}/` | 6 (three works, a contributor, a character, a merge cluster) | **OK** |
| 2026-10-25 | `GET /api/v1/index/entities/{id}/relations/` | 5 (two ordinary, the three with the most relations) | **OK** |
| 2026-10-25 | `GET /api/v1/index/entities/{id}/credits/` | 4 (the three with the most credits, plus a merge cluster) | **OK** |
| 2026-10-25 | `GET /api/v1/index/entities/{id}/releases/` | 4 (the three with the most release links, plus a merge cluster) | **OK** |
| 2026-10-25 | regression: collections, detail, metrics, relations, credits, releases, 404 | one entity each | **7/7 OK** |
| 2026-10-25 | `GET /api/v1/index/entities/{id}/characters/` (pages 1 and 2) | 3 entities | **OK** — `next`/`previous` ignored, they carry each host |
| 2026-10-25 | `GET /api/v1/index/entities/{id}/episodes/` (pages 1, 2, custom size, past last) | 4 entities | **OK** |
| 2026-10-25 | `GET /api/v1/index/entities/` — default, page 2, collection, query, scope=all, popular, subject type, nsfw | 8 variants | **OK** |
| 2026-10-25 | `GET /api/v1/index/entities/{id}/evidence/` | 3 entities | **OK** — compared as a set (`--unordered $`) |
| 2026-10-25 | `GET /api/v1/index/collections/{slug}/entities/` — anime, galgame, query, unknown slug | 4 variants | **OK** |
| 2026-10-25 | shadow run | 10 random entities × 8 endpoints | **80/80 matched** |
| 2026-10-25 | shadow run | 30 random entities × 8 endpoints | **240/240 matched** |
| 2026-10-25 | shadow run | 12 entities × 8 endpoints + 7 list paths | **103/103 matched** |
| 2026-10-25 | `GET /api/v1/auth/social/providers/` | 1 | **OK** — both report GitHub disabled, matching the environment |
| 2026-10-25 | `GET /api/v1/index/calendar/events/` — weekly board, include_work, range, range+timezone, range+include_work | 5 variants | **OK** |
| 2026-10-25 | `GET /api/v1/index/calendar/board/events/` — default, include_work | 2 variants | **OK** |
| 2026-10-25 | `POST /api/v1/auth/sessions/password/` — wrong credentials | 1 | **OK** — identical problem body |
| 2026-10-25 | `POST /api/v1/auth/sessions/password/` — valid credentials | 1 | **OK** — same claims; Django accepts the token this service minted |
| 2026-10-25 | `GET /api/v1/users/me/profile/` — no token, Django-created profile, service-created profile | 3 | **OK** — 401 identical; both creations produce the same body |
| 2026-10-25 | `PATCH /api/v1/users/me/profile/` — empty, bad colour, valid, blank colour | 4 | **OK** — same validation bodies and same updated profile |
| 2026-10-25 | `GET /api/v1/community/me/notifications/unread-count/` | 1 | **OK** |
| 2026-10-25 | `PUT` / `DELETE /api/v1/community/me/blocks/{user_id}/` | 2 | **OK** — response and rows match; the creation time is per-request |
| 2026-10-25 | `GET /api/v1/community/me/blocks/`, `GET /api/v1/community/me/mutes/` | 2 | **OK** |
| 2026-10-25 | `PUT` / `DELETE /api/v1/community/me/following/{user_id}/` | 2 | **OK** — the follow row, the activity it writes and the notification for the target all match |
| 2026-10-25 | `GET /api/v1/community/me/followers/`, `GET /api/v1/community/me/following/` | 2 | **OK** |
| 2026-10-25 | `GET /api/v1/community/users/{id}/followers/`, `/following/` — present and missing user | 3 | **OK** — the missing account is `users.user_not_found`, not a bare 404 |
| 2026-10-25 | `POST /api/v1/auth/session/` — with a refresh cookie | 1 | **OK** — both answer 204 and add one blacklisted token |
| 2026-10-25 | shadow run after the community block | 10 entities × 8 endpoints + 11 list paths | **91/91 matched** |
| 2026-10-25 | `GET /api/v1/community/me/reports/` | 1 | **OK** — a report on an activity, with its target and people |
| 2026-10-25 | `PUT /api/v1/community/me/notifications/{id}/read-state/` | 1 | **OK** — same body; `read_at` is stamped per call and compared with it ignored |
| 2026-10-25 | `GET /api/v1/community/me/notifications/` — first page with `page_size=2` | 1 | **OK** — same rows and the same decoded `next` cursor |
| 2026-10-25 | shadow run after the auth and community blocks | 8 entities × 8 endpoints + 11 list paths | **75/75 matched** |
| 2026-10-25 | `GET /api/v1/users/me/tags/`, `POST` with a new name and with a blank one | 3 | **OK** — the create is get-or-create, so the second call answers 200 where the first answered 201 |
| 2026-10-25 | `PATCH` / `DELETE /api/v1/users/me/tags/{id}/` | 3 | **OK** — same rename body, 404 for an unknown id, 204 for the delete |
| 2026-10-25 | `GET /api/v1/users/me/profile/stats/` — two years and zones, one unknown zone | 3 | **OK** — the aggregates and the calendar agree, and the unknown zone is the same 400 |
| 2026-10-25 | `GET /api/v1/users/me/library/entries/` — default and filtered | 2 | **OK** — the entry, its entity summary and its release states |
| 2026-10-25 | `GET /api/v1/users/me/library/entries/{id}/` | 1 | **OK** — the same row the list returns |
| 2026-10-25 | `PATCH /api/v1/users/me/library/entries/{id}/` — bad status, bad rating, inverted watch dates | 3 | **2 OK, 1 deliberate difference** |
| 2026-10-25 | `POST /api/v1/users/me/library/entries/` — create, add again, missing status, unknown entity | 4 | **OK** — the second add answers 200 where the first answers 201 |
| 2026-10-25 | `PUT /api/v1/users/me/library/entries/{id}/releases/{release_id}/` — bad status, valid state | 2 | **1 OK, 1 deliberate difference** |
| 2026-10-25 | `GET` / `PUT /api/v1/users/me/library/entries/{id}/tags/` | 2 | **GET OK; PUT deliberate difference** (Django answers 500) |
| 2026-10-25 | `PUT /api/v1/users/me/library/entries/{id}/rating-details/` | 1 | **deliberate difference** (Django answers 500; this one 200 with both details) |
| 2026-10-25 | `GET /api/v1/users/me/library/entries/{id}/reviews/` | 1 | **OK** — the review, its entity summary, reaction count and viewer flags |
| 2026-10-25 | `POST /api/v1/users/me/library/entries/{id}/reviews/` | 1 | **OK** — same body once the id and timestamps are set aside |
| 2026-10-25 | `GET /api/v1/community/moderation/reports/` — as staff | 1 | **OK** — the same queue, ordered the same way |
| 2026-10-25 | `POST /api/v1/community/reports/` — unknown target, bad reason, a real report | 3 | **OK** — same domain 404, same field error, same created body |
| 2026-10-25 | `GET /api/v1/community/me/bookmarks/` — a review and a collection | 1 | **OK** — both branches, each rendered by its own summary |
| 2026-10-25 | `PUT /api/v1/community/me/bookmarks/{type}/{id}/` — hidden target, public collection | 2 | **OK** — the same 404 and the same created row |
| 2026-10-25 | `POST /api/v1/community/reports/` — a hidden review as the target | 1 | **OK** — the same 404, from the shared visibility rule |
| 2026-10-25 | `GET /api/v1/users/{id}/` — an existing account and a missing one | 2 | **OK** — the five counts and the 404 |
| 2026-10-25 | `PUT /api/v1/community/me/reactions/{type}/{id}/{reaction}/` — a collection, an unsupported type | 2 | **OK** — same body and same 400 |
| 2026-10-25 | `GET /api/v1/community/me/activities/` | 1 | **OK** — the full activity payload, including the borrowed entity |
| 2026-10-25 | `GET /api/v1/community/activities/`, `/users/{id}/activities/` | 2 | **OK** — the public filter and the viewer exclusions |
| 2026-10-25 | `GET /api/v1/community/me/feed/` — default and `include_self` | 2 | **OK** |
| 2026-10-25 | `GET /api/v1/community/posts/` — default and by keyword | 2 | **OK** — author, entity summary and the three viewer flags |
| 2026-10-25 | `POST /api/v1/community/posts/` | 1 | **OK** — same body and one timeline entry per post |
| 2026-10-25 | `GET /api/v1/community/posts/{id}/` — an existing post and a missing one | 2 | **OK** — including the domain 404 |
| 2026-10-25 | `PATCH` / `DELETE /api/v1/community/posts/{id}/` | 3 | **PATCH OK**; the locked 409 and the 204 match; deleting removes the timeline entry |
| 2026-10-25 | `GET /api/v1/community/posts/{id}/comments/` + a missing post | 2 | **OK** — the list and the post's own 404 |
| 2026-10-25 | `POST /api/v1/community/posts/{id}/comments/` | 1 | **OK** — same body, and the post's reply count goes up by one on each |
| 2026-10-25 | `PATCH` / `DELETE /api/v1/community/comments/{id}/` + a missing comment | 3 | **OK** — the edit, the 204 and the domain 404 |
| 2026-10-25 | `PATCH /api/v1/community/moderation/posts/{id}/` — hide | 1 | **OK** — the post answers with the hidden feed policy |
| 2026-10-25 | `PATCH /api/v1/community/moderation/comments/{id}/` — hide | 1 | **OK** — the comment answers hidden, with no author |
| 2026-10-25 | `PATCH /api/v1/community/moderation/reports/{id}/` — rejected | 1 | **OK** — same status and resolver |
| 2026-10-25 | `GET /api/v1/users/{id}/collections/` | 1 | **OK** — counts, viewer flags and ordering |
| 2026-10-25 | `GET` / `POST /api/v1/users/me/collections/` | 2 | **OK** — the list keeps private rows; the created body matches |
| 2026-10-25 | `GET /api/v1/users/me/collections/{id}/` + a missing one | 2 | **OK** — the body and the 404 wording |
| 2026-10-25 | `GET` / `POST /api/v1/users/me/collections/{id}/items/` | 2 | **OK** — the list and the added item |
| 2026-10-25 | `PATCH` / `DELETE /api/v1/users/me/collections/{id}/items/{item}/` | 2 | **PATCH OK**, 204 |
| 2026-10-25 | `GET /api/v1/auth/social/providers/` | 1 | **OK** — the GitHub entry and its enabled flag |
| 2026-10-25 | `POST /api/v1/auth/registrations/` — a fresh account and a taken nickname | 2 | **201 with an access token**; the conflict body matches |
| 2026-10-25 | `POST /api/v1/auth/sessions/code/`, `/auth/password-resets/` | 2 | **OK** — access token on both; the reset answers 204 |
| 2026-10-25 | `POST /api/v1/auth/verification-codes/` — no captcha token | 1 | **OK** — the same `users.invalid_captcha` |
| 2026-10-25 | `GET /api/v1/operations/import-jobs/{id}/` + a missing job | 2 | **OK** — a job whose type has no provider is a 404, and a missing job is `sync.job_not_found` |
| 2026-10-25 | `GET /api/v1/operations/sync/{id}/` + a missing campaign | 2 | **OK** — the campaign, its progress block and the 404 |
| 2026-10-25 | `GET /api/v1/operations/sync/{id}/items/` | 1 | **OK** — the items, ordered by shard then id |
| 2026-10-25 | `PUT /api/v1/community/me/notifications/read-state/` | 1 | **OK** — both report two updated and leave zero unread (compared by state, because each call mutates) |
| 2026-10-25 | `GET`/`PATCH /api/v1/users/me/settings/` — read, empty, bad choice, bad colour, adult without confirmation, valid choices, adult with confirmation | 7 | **OK** — the confirmation timestamp is per-request and compared with it ignored |

Reproduce against the two services sharing a database:

```bash
uv run python scripts/parity.py \
  --old http://127.0.0.1:8008 --new http://127.0.0.1:8010 \
  --path /api/v1/index/entities/<id>/metrics/
```

Two divergences were found by this comparison and fixed or recorded:

1. **Lifecycle check.** The new service required `active` of every entity in the
   merge cluster; Django requires it of the resolved entity only. Fixed.
2. **404 envelope.** Django answers with `application/problem+json`
   (`type`, `title`, `status`, `detail`, `instance`, `trace_id`); FastAPI's
   default is `{"detail": ...}`. Reproduced in `shared/problems.py`; `trace_id`
   is random per request, hence `--ignore trace_id`. A non-uuid path answers 404
   like Django's URL converter, but only the status is parity there because
   Django renders HTML for an unmatched route.
3. **Names come from the cluster.** The first detail run returned 18 names on
   the Django side and 9 on this one: names, descriptions and media are read
   across every entity redirected into the root, not from the root alone.
4. **Provenance uses the row's own record.** A contributor's names all cited the
   staff record in Django; this service cited each name's observation record.
   `field_provenance` reads `name.provider_record`, and so must the SQL.
5. **Relation ids are bigint.** `entity_relation.id` is an `AutoField`, unlike the
   fact tables where the key is a UUID. Passing strings into `uuid[]` made every
   relation list answer 500.
6. **Performance.** The heaviest relation list (1.5 MB) takes **68.5 s** on the
   Django side and **7.6 s** on this one, with identical bytes. The parity tool's
   fixed 30-second timeout reported that as a failure of the new service; it is
   now `--timeout`.
7. **The summary reads current names only.** `preferred_name` runs over
   `current_entity_names()`; the first implementation read every name in the
   cluster, so a contributor with five spellings picked the oldest row. The
   difference was one glyph (`DanieI` against `Daniel`), which only a byte
   comparison finds.
8. **Evidence order is not a contract.** Django's `prefetch_related` has no
   `ORDER BY`, so the order it returns is PostgreSQL's physical order. This
   service orders by id; the comparison sorts declared paths
   (`--unordered facts[].evidence`) and still fails on a real set difference.
9. **A page past the last one is a 404.** Django raises `Invalid page.`; this
   service returned an empty 200.
10. **The problem `instance` keeps the query string.** Django builds it from the
   full path, so a page-two 404 cites `?page=2`.
11. **The batched summary is not the single summary.** Django's
   `entity_summaries` (list) keys members by id, so its "cluster" is the root
   alone: names, memberships, media, audience and the spoiler gate all follow the
   root, while `entity_summary` (detail, relations, credits) follows the merge
   cluster. A merged work therefore shows fewer covers and a different audience in
   the list. Reproduced with a `cluster_scope` flag; the inconsistency is worth
   removing on both sides.
12. **Currency is decided by the row's own observation.** `CURRENT` first read
   `record.status` and the provider policy through the provenance join, which for
   a cover is the asset's record; Django reads them from the observation's record.
13. **Bare lists have no order.** `evidence` returns a list with no `ORDER BY`, so
   Django's order is the table's physical order; this service orders by id and
   the comparison sorts the root array (`--unordered $`).
14. **Two collapse rules, not one.** Django resolves keyword matches to the final
   root (`resolve_with`, whole chain) but collapses memberships by a single hop
   (`_canonical_filter`). Keyword matching also reads only *current* names and
   links; searching every row returned one stale match.
15. **The calendar always builds the work summary.** It decides whether a work
   appears at all and hides adult entries, even when the caller did not ask for
   the summary; and DRF renders the nullable `work` field as `null`, so the key is
   always present.
16. **The password digest claim is `hash_password`.** Not SimpleJWT's default
   name; tokens carry it under the name the service already issues. A token minted
   here is accepted by Django (`GET /api/v1/users/me/profile/` returns 200), which
   is the check that matters.
17. **Inverted watch dates crash Django.** `PATCH` with `watch_end_date` before
   `watch_start_date` answers **500** from the Django service and **400** with the
   field error from this one. The check exists in Django and is written before the
   save, so the crash is in the old service, not in the rule. Matching a 500 was
   not considered correct; the difference is recorded rather than reproduced.
18. **A valid release state crashes Django.** `PUT` with a good body answers
   **500** from the Django service and **201** from this one. The state needs
   `language` and `platform`, which the serializer does not default; the port
   writes empty strings, which is what the column copies had. Recorded, not
   reproduced.
19. **Replacing an entry's tags crashes Django.** The same body answers **500** from
   the Django service and 200 with the two tags from this one. The four crashes
   found so far (inverted dates, a valid release state, tag replacement) are the
   strongest argument for the rewrite: a service that answers 500 on a legal
   request has no client contract to preserve.
20. **Rating details crash Django too.** A valid two-item replacement answers 500
   from the Django service and 200 from this one. That is the fifth legal write the
   old service cannot complete — the group is now the strongest single argument
   for the rewrite.
21. **Removing a reaction leaves the counter.** `DELETE` removes the row and does
   not decrement `reaction_count`, so the number drifts upward over time. The port
   does the same: the counter is part of the old contract, and the drift is a bug
   to fix once, on both sides, not something one side should quietly correct.
22. **The verification mail is delivered, but its copy is shorter.** The port sends
   through the same provider and key the old service uses, inline instead of Celery;
   a provider failure is logged and never turns a written code into a failed request.
   The branded template is not reproduced — subject and code match, the body does not.
23. **A job type without a provider is a 404, not a body.** `subject_bangumi` is a real
   `sync_job` row, but Django maps the type to a registered import provider and answers
   `Import job not found.` when there is none. Read the diff direction carefully: the
   404 was the old service's, not a tool error.
24. **`value` type.** The OpenAPI snapshot says string, the Django response sends
   a number. Parity copies the response; the disagreement is recorded in
   `contexts/signal/domain.py` for a deliberate fix on both sides.
