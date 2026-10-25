# Parity

Every endpoint is compared with the Django service before traffic moves. The tool
is `scripts/parity.py`; it compares status codes, then the document structurally
(dict keys as sets, list order significant, numbers by value).

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
14. **`value` type.** The OpenAPI snapshot says string, the Django response sends
   a number. Parity copies the response; the disagreement is recorded in
   `contexts/signal/domain.py` for a deliberate fix on both sides.
