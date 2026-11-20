# Noshiro DB Web

The React application provides catalogue discovery, entity relationships,
personal library tools, reviews, collections, and community activity. It
supports Chinese, English, and Japanese.

The app uses Node.js 24 and the pnpm release pinned in `package.json`.
Run its commands from `apps/web`.

```sh
corepack enable pnpm
pnpm install --frozen-lockfile
cp .env.example .env
pnpm dev
```

Vite forwards API calls to a local backend on port 8008 by default. Follow
the [repository setup](../../README.md#local-development) to start that backend.
`pnpm check` runs the full Web quality suite.

- [Development](docs/development.md) covers the proxy, app commands, and testing.
- [Architecture](docs/architecture.md) explains source layers and boundaries.
- [Deployment](docs/deployment.md) covers the static build and public API origin.
