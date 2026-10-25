# Parity

Every endpoint is compared with the Django service before traffic moves. The tool
is `scripts/parity.py`; it compares status codes, then the document structurally
(dict keys as sets, list order significant, numbers by value).

## Evidence log

| Date | Endpoint | Cases | Result |
|---|---|---|---|
| 2026-10-25 | `GET /api/v1/index/entities/{id}/metrics/` | 4 entities (one merged cluster of 3, three largest by metric count) | **OK, zero differences** |
| 2026-10-25 | same, unknown entity | 404 | **OK** — same `application/problem+json` envelope (`trace_id` ignored) |

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
3. **`value` type.** The OpenAPI snapshot says string, the Django response sends
   a number. Parity copies the response; the disagreement is recorded in
   `contexts/signal/domain.py` for a deliberate fix on both sides.
