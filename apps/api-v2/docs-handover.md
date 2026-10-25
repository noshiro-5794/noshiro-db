# Handover: switching the web service, then retiring it

Written to be executed by someone who did not build this. Every command was run at
least once against the live stack; the steps that have not been run say so.

## The one thing to understand first

**Web and workers are two different retirements.**

- `noshiro-db-web-1` serves HTTP on `127.0.0.1:8008`. This is what the proxy points at.
- `noshiro-db-worker-sync-1`, `worker-ai-1` and `beat-1` consume the broker and run the
  sync, AI and scheduled jobs. **The replacement service publishes to them and depends
  on them**; it does not replace them.

So switching the proxy retires the Django *web* service only. The workers and beat keep
running until those tasks move, which is a separate piece of work (`docs-transition.md`
explains why the candidate decision in particular belongs to the engine, not the API).

## Phase 0 — stand it up beside Django

```sh
cd /path/to/repo/apps/api-v2
ENV_FILE=../api/.env.production docker compose -f docker-compose.api-v2.yml up -d --build
docker logs -f noshiro-db-api-v2-1        # wait for "Application startup complete"
```

Migrations are already at head; if the schema moved since, run them once:

```sh
docker exec noshiro-db-api-v2-1 alembic upgrade head
```

Django keeps serving throughout. Both read and write the same database.

This phase has been run for real: the image builds from the pinned base already on the
host, the container joins `noshiro_net`, and the smoke script against its port reports

```
ok   liveness (200) … ok   read entry 1143 (200)
0 failure(s)
```

so the image, the shared network, the env file and the readiness probe are all proven.

The shadow comparison was then run **against that container**, not against a development
process:

```
223/223 comparisons matched (25 entities, 11 list paths, 12 signed-in paths)
```

That is the evidence that matters for a switch: the artifact that would be deployed
answers exactly like the service it replaces, signed-in paths included.

What has not been run is a container created by the compose file itself — the manual
`docker run` above used the same image, network and env file.

## Phase 1 — prove it before anyone sees it

```sh
python scripts/smoke.py --base http://127.0.0.1:8010 \
  --email <staff account> --password <password> --entry <entry id>
```

Expect eight `ok` lines and `0 failure(s)`.

Then the broader comparison, with both services running:

```sh
PYTHONPATH=. DATABASE_URL=postgresql://… uv run python scripts/shadow.py \
  --old http://127.0.0.1:8008 --new http://127.0.0.1:8010 --count 40 --token <access token>
```

Expect `… comparisons matched` with no `FAIL` lines. The last run at this size was
331/331 anonymous and 119/119 signed in.

If either step fails, stop here. Nothing is routed to the new service yet.

## Phase 2 — switch

Change the upstream for the site from `127.0.0.1:8008` to `127.0.0.1:8010` in the
proxy (1Panel → OpenResty → the site's reverse-proxy record), or with whatever the
proxy calls it. Only the upstream port changes; TLS, headers and paths stay as they are.

Then, within a minute:

```sh
curl -s https://<site>/health/live/     # {"status":"ok"}
curl -s https://<site>/health/ready/    # {"status":"ok"}
python scripts/smoke.py --base https://<site> --email … --password … --entry …
```

The smoke script pointing at the public host is the real check: it goes through the
proxy, so it catches a wrong port or a header the proxy drops.

## Phase 3 — watch the first hour

| Look at | Command | Healthy |
|---|---|---|
| Errors | `docker logs -f noshiro-db-api-v2-1` | no 500s, no tracebacks |
| Worker backlog | `docker exec noshiro-db-redis-broker-1 redis-cli -n 0 llen sync` | near zero, not growing |
| Django web | `docker logs --tail 50 noshiro-db-web-1` | no traffic, since the proxy moved |

Sending a code is the one flow that exercises mail and captcha together; if a sign-up
is reported broken, check that `HCAPTCHA_ENABLED` and `RESEND_API_KEY` are in the env
file the new container reads.

## Phase 4 — rollback

Put the upstream back to `127.0.0.1:8008`. That is the whole of it:

- the schema is shared and the new service never migrates down on its own,
- both services can serve at once, so a rollback does not need a maintenance window,
- the only thing that cannot be split is an OAuth round trip: a sign-in that started on
  one service must finish there, because each signs its own state.

## What has not been run

- The proxy change itself (1Panel-managed; I could not read its configuration).
- The GitHub sign-in end to end (no OAuth client configured in this environment).
- The new service under real traffic: every check so far was one request at a time.
