# Parity

Every endpoint is compared with the Django service before traffic moves. The tool
is `scripts/parity.py`; it compares status codes, then the document structurally
(dict keys as sets, list order significant, numbers by value).

## Evidence log

| Date | Endpoint | Entities | Result |
|---|---|---|---|
| 2026-10-25 | `GET /api/v1/index/entities/{id}/metrics/` | 4 (one merged cluster of 3, three largest by metric count) | **4/4 OK, zero differences** |

Reproduce against the two services sharing a database:

```bash
uv run python scripts/parity.py \
  --old http://127.0.0.1:8008 --new http://127.0.0.1:8010 \
  --path /api/v1/index/entities/<id>/metrics/
```

Two divergences were found by this comparison and fixed or recorded:

1. **Lifecycle check.** The new service required `active` of every entity in the
   merge cluster; Django requires it of the resolved entity only. Fixed.
2. **`value` type.** The OpenAPI snapshot says string, the Django response sends
   a number. Parity copies the response; the disagreement is recorded in
   `contexts/signal/domain.py` for a deliberate fix on both sides.
