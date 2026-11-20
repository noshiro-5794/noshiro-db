# Noshiro DB

Noshiro DB is a knowledge base, personal library, and community for anime, manga,
games, and related media. Explore connections between works, characters, creators,
and releases, then organize your library with progress, reviews, and collections.

[Browse Noshiro DB](https://app.noshiro.moe) · [Documentation](docs/README.md)

## Local development

Use Docker Compose for local PostgreSQL and Redis, Python 3.13 with uv for the
API, and Node.js 24 with the pnpm version pinned by the Web app.

From the repository root:

```sh
make dev-up
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
make api-install
make web-install
make api-migrate
```

Run `make api-run` and `make web-dev` in separate terminals. Open
`http://localhost:5173`. The local API listens on port 8008. Configure
`JWT_SECRET` in `apps/api/.env` to test sign-in.

## Repository layout

| Path | Responsibility |
| --- | --- |
| [apps/api](apps/api/README.md) | FastAPI, PostgreSQL schema, Celery, and MCP |
| [apps/web](apps/web/README.md) | React application, API client, and browser tests |
| [deploy](deploy/README.md) | Development infrastructure and production deployment |
| [docs](docs/README.md) | Product scope and system architecture |

`make check` runs both application suites. Use `make openapi` to regenerate the
API contract when changing request or response shapes.

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [AGPL-3.0-only](LICENSE)
