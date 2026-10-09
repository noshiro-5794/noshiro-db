# Contributing

Noshiro DB is a two-app repository: a Django API in `apps/api` and a React client
in `apps/web`. Work inside the app you are changing and run that app's gates
before opening a pull request.

## Setup

`apps/api/README.md` and `apps/web/README.md` cover prerequisites and the local
environment. In short: `uv sync` plus the infra compose file for the API,
`pnpm install` plus `.env` for the web client.

## Checks

```bash
make check        # both apps
make api-check    # ruff, pytest, Django checks, migration drift
make web-check    # format, types, lint, unit, e2e, build
```

CI runs the same commands, scoped by path: a change under `apps/web/` does not
build the API container, and the API suite does not run for web-only changes.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): what
changed`, with a body that explains why when the reason is not obvious from the
diff. Scopes name the area, not the layer — `feat(search):`, `fix(sync):`,
`refactor(web):`.

Inside `apps/web`, `pnpm commit` walks through the same format.

## Contract Changes

The API is the source of truth for request and response shapes. When an endpoint
changes, regenerate the committed schema (`make openapi`) and update the web
client's contracts and decoders in the same pull request, so the two apps never
disagree about a payload.
