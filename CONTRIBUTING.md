# Contributing

Noshiro DB Frontend is a React, TypeScript, and Vite application for the Noshiro DB project.

## Local Setup

```bash
source ~/.nvm/nvm.sh
nvm use 20
npm install
cp .env.example .env
npm run dev
```

Set the local API endpoint in `.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8008
VITE_HCAPTCHA_SITE_KEY=
```

## Development Checks

Run these before opening a pull request or pushing a release branch:

```bash
npm run typecheck
npm run lint
npm run build
```

## Commit Style

Use Commitizen-style conventional commits:

```text
feat: add subject graph page
fix: correct review spoiler rendering
docs: update development guide
refactor: simplify library query options
```

Prefer small, scoped commits when possible:

- `feat` for user-visible product work
- `fix` for bugs and regressions
- `docs` for README or documentation-only changes
- `style` for visual-only polish without behavior changes
- `refactor` for internal structure changes without behavior changes
- `chore` for tooling or maintenance

## Project Boundaries

- `src/app` owns providers, app shell, and global layout.
- `src/features` owns domain modules, API wrappers, query options, and feature components.
- `src/lib` owns technical infrastructure such as the API client and query client.
- `src/pages` owns route-level composition.
- `src/shared/ui` owns reusable UI primitives without domain ownership.

Avoid committing generated files such as `dist/`, `node_modules/`, `*.tsbuildinfo`, or local `.env` files.

## Copy and i18n

The product contains anime and galgame entries. Keep subject-level wording neutral:

- Prefer `planned`, `in progress`, `completed`, `on hold`, and `dropped` for Library status.
- Avoid anime-only wording such as "watching" for subject-level state.
- Episode-specific controls may use watched language because they refer to anime episodes.
- Keep Chinese, English, and Japanese message keys aligned in `src/features/i18n/messages.ts`.
