# Contributing

Start with the [local setup](README.md#local-development) and the architecture
guide for the app you are changing. Python dependencies belong to
[apps/api](apps/api/docs/architecture.md), and Node dependencies belong to
[apps/web](apps/web/docs/architecture.md).

## Check your change

| Command | Coverage |
| --- | --- |
| `make check` | API and Web checks |
| `make api-check` | Python lint, typing, contract inventories, and tests |
| `make web-check` | Formatting, types, lint, unit and browser tests, and build |

GitHub runs both quality jobs for pull requests. A separate job checks the
PostgreSQL migration sequence and transaction tests.

## Change an API payload

1. Update the FastAPI route and its schema.
2. Run `make openapi`.
3. Update the matching contracts and decoders in `apps/web/src/shared/api/`.
4. Run both application checks.

Use Alembic for database changes. Include a migration and verify it on a
disposable database when the change alters the schema.

## Name changes for their purpose

Use branch names such as `fix/session-refresh` or
`refactor/provider-adapters`. Commit titles follow
[Conventional Commits](https://www.conventionalcommits.org/), for example
`fix(auth): preserve refresh cookie scope`. Use the body to explain the reason
and record decisions that the diff cannot convey.

A pull request should describe the behavior change, how it was checked, and any
deployment or data migration steps the reviewer needs to verify.
