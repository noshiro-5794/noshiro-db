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

CI runs the same commands. Every pull request runs both suites, because the
branch rules require the `api quality` and `web quality` checks and a check that
is never reported blocks the merge instead of protecting it. The path filters
still apply to pushes to `main`, so a merge only rebuilds what it changed.

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

## History

On 2026-10-21 the history was rewritten once: `__pycache__` bytecode that had
been committed by accident was purged from every commit, and the author
identities were normalised, so **every commit SHA changed**. The shape of the
history was kept — the two `git subtree` imports of the original API and web
repositories, their root commits, and every commit message are untouched.

Consequences: a clone made before that date must be re-cloned or hard-reset onto
the new `main`, and any SHA or branch name recorded before it no longer exists.
`.mailmap` keeps `git shortlog` showing one author even though GitHub signs the
commits it generates with a noreply address.
