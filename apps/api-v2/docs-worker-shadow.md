# Shadow runs: popularity

The first write-path task moved off Django is the popularity rebuild, and it is the first
one with a recorded old-vs-new comparison.

## What was compared

The computed standing per entity — the value that decides catalogue order. Nothing was
written: both sides expose the computation without persisting it, which is the only way to
compare on a live database without changing it.

| | |
|---|---|
| Django side | `PopularityService._rank` over both primary signals |
| Replacement side | `worker.catalogue.score_map` |
| Entities compared | 89,318 |
| Input | the production database, read-only |

## Result

```
entities: django 89318 ours 89318 | same set: True
differing values: 0
```

## What the first attempt found

The initial port computed **one percentile across anime and galgame together**. The
comparison caught it immediately:

```
entities: django 89318 ours 89318 | same set: True
differing values: 62089
```

A percentile is only meaningful inside one series: AniList counts list members, VNDB counts
ratings, so merging the two populations before ranking compares numbers that count
different things. The fix ranks each signal inside its own population and merges the
standings afterwards.

This is the case the shadow rule exists for. The code compiled, the tests passed, and the
numbers were wrong for 70% of the catalogue.

## Reproducing it

Django side, run from a one-off container of the app image:

```sh
docker run --rm --network noshiro_net --env-file "$ENV_FILE" -w /app/src \
  --entrypoint python noshiro-db/api:prod -c '
import json, os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
django.setup()
from apps.index.services.popularity import PRIMARY_SIGNALS, popularity_service
from apps.index.services.resolution import entity_resolution_service
redirects = entity_resolution_service.redirect_map()
scores = {}
for signal in PRIMARY_SIGNALS:
    scores.update(popularity_service._rank(signal, redirects))
print(json.dumps({str(k): str(v) for k, v in scores.items()}))
' > /tmp/django_scores.json
```

Replacement side, with `score_map`:

```sh
PYTHONPATH=apps/api-v2/src DATABASE_URL=… python -c '
import asyncio, json
from api.worker import catalogue
from api.worker.session import _sessions
async def main():
    async with _sessions() as s:
        scores = await catalogue.score_map(s)
    print(json.dumps({str(k): str(v) for k, v in scores.items()}))
asyncio.run(main())
' > /tmp/ours_scores.json
```

Then diff the two JSON objects.

## What is not covered yet

The **persistence** step — the `UPDATE work …` and the stale-row clearing — is not part of
this comparison. It needs a run that is allowed to write, in a scratch database or with a
recorded reversal, because its effect is a change to every work row.
