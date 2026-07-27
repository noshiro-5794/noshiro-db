# Development

## Requirements

- Node.js 24 LTS
- fnm 1.39+
- pnpm 11
- A running Noshiro DB backend API

When the shell does not load Node automatically, activate the project runtime first:

```bash
fnm use --install-if-missing
corepack enable pnpm
```

## Setup

```bash
pnpm install --frozen-lockfile
cp .env.example .env
```

The default development configuration connects to the deployed backend through Vite's same-origin proxy:

```text
API_PROXY_TARGET=https://api.noshiro.moe
VITE_API_BASE_URL=
VITE_HCAPTCHA_SITE_KEY=
```

The proxy keeps the browser on the local origin and avoids weakening production CORS/CSRF policy. To develop against the sibling backend repository instead, set `API_PROXY_TARGET=http://127.0.0.1:8008`.

## Scripts

```bash
pnpm dev
pnpm format
pnpm typecheck
pnpm lint
pnpm test
pnpm test:watch
pnpm build
pnpm preview
pnpm check
pnpm check:dependencies
```

## Remote Development

When developing over SSH, expose the Vite dev server explicitly:

```bash
pnpm dev --host 0.0.0.0
```

When using the deployed API, only the frontend port needs forwarding:

```bash
ssh -N -L 5173:127.0.0.1:5173 user@example.com
```

Forward port `8008` as well only when `API_PROXY_TARGET` points to a backend running on the remote development host:

```bash
ssh -N -L 5173:127.0.0.1:5173 -L 8008:127.0.0.1:8008 user@example.com
```

If the forwarded frontend port refuses connections, confirm the Vite server is running and bound with `--host 0.0.0.0`. If the backend port refuses connections, confirm the backend process is running on the remote host and listening on the forwarded port.

## API Contract Notes

- Auth, profile, subject marks, progress, tags, reviews, collections, and public profile APIs live under `/api/users/`.
- Community follow, follower, activity, feed, notification, bookmark, reaction, comment, and report flows live under `/api/community/`.
- Admin sync APIs live under `/api/admin/` or the backend sync/admin route group, depending on backend deployment.
- Transport contracts live in `src/shared/api/contracts/`. Domain API clients and query definitions stay in their
  owning entity or feature slice.

## UI and Copy Notes

- Library status labels are intentionally neutral so anime and galgame entries both fit: planned, in progress, completed, on hold, and dropped.
- Episode progress copy may still use watched language because episode tracking applies to anime chapters.
- Public docs content in `src/pages/docs/content/docs.ts` is frontend-owned content and does not depend on the backend.

## Quality Gates

Run these commands before committing:

```bash
pnpm check
```

## Git Hygiene

Do not commit generated artifacts or machine-local configuration:

- `dist/`
- `node_modules/`
- `*.tsbuildinfo`
- `.env`
- local agent/tooling directories such as `.agents/` and `.codex/`

Keep `.env.example`, `README.md`, `docs/`, and public static assets in the repository.
