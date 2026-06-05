# Development

## Requirements

- Node.js 20+
- npm
- A running Noshiro DB backend API

When the shell does not load Node automatically, activate the project runtime first:

```bash
source ~/.nvm/nvm.sh
nvm use 20
```

## Setup

```bash
npm install
cp .env.example .env
```

Update `.env` for your local backend:

```text
VITE_API_BASE_URL=http://127.0.0.1:8008
VITE_HCAPTCHA_SITE_KEY=
```

## Scripts

```bash
npm run dev
npm run typecheck
npm run lint
npm run build
npm run preview
```

## Remote Development

When developing over SSH, expose the Vite dev server explicitly:

```bash
npm run dev -- --host 0.0.0.0
```

If the backend runs on a different port, forward both the frontend and backend ports through your SSH tunnel.

Example tunnel from a local machine:

```bash
ssh -N -L 5173:127.0.0.1:5173 -L 8008:127.0.0.1:8008 user@example.com
```

If the forwarded frontend port refuses connections, confirm the Vite server is running and bound with `--host 0.0.0.0`. If the backend port refuses connections, confirm the backend process is running on the remote host and listening on the forwarded port.

## API Contract Notes

- Auth, profile, subject marks, progress, tags, reviews, collections, and public profile APIs live under `/api/users/`.
- Community follow, follower, activity, feed, notification, bookmark, reaction, comment, and report flows live under `/api/community/`.
- Admin sync APIs live under `/api/admin/` or the backend sync/admin route group, depending on backend deployment.
- Frontend API clients keep domain ownership in `src/features/*/api.ts` and query options in `*-queries.ts`.

## UI and Copy Notes

- Library status labels are intentionally neutral so anime and galgame entries both fit: planned, in progress, completed, on hold, and dropped.
- Episode progress copy may still use watched language because episode tracking applies to anime chapters.
- Public docs content in `src/features/docs/content/docs.ts` is frontend-owned content and does not depend on the backend.

## Quality Gates

Run these commands before committing:

```bash
npm run typecheck
npm run lint
npm run build
```

## Git Hygiene

Do not commit generated artifacts or machine-local configuration:

- `dist/`
- `node_modules/`
- `*.tsbuildinfo`
- `.env`
- local agent/tooling directories such as `.agents/` and `.codex/`

Keep `.env.example`, `README.md`, `docs/`, and public static assets in the repository.
