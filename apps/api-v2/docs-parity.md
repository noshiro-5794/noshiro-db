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
5. **`value` type.** The OpenAPI snapshot says string, the Django response sends
   a number. Parity copies the response; the disagreement is recorded in
   `contexts/signal/domain.py` for a deliberate fix on both sides.
