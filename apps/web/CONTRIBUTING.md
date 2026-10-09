# Contributing

Noshiro DB Frontend is a React, TypeScript, and Vite application for the Noshiro DB project.

## Local Setup

```bash
fnm use --install-if-missing
corepack enable pnpm
pnpm install --frozen-lockfile
cp .env.example .env
pnpm dev
```

Local development connects to the deployed API through Vite's same-origin proxy:

```text
API_PROXY_TARGET=https://api.noshiro.moe
VITE_API_BASE_URL=
VITE_HCAPTCHA_SITE_KEY=
```

Set `API_PROXY_TARGET=http://127.0.0.1:8008` when working against a local backend.

## Development Checks

Run these before opening a pull request or pushing a release branch:

```bash
pnpm check
```

## Commit Style

Use Conventional Commits:

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

- Dependencies flow from `app` to `pages`, `widgets`, `features`, `entities`, and finally `shared`.
- `src/app` owns bootstrap, providers, the router, the application shell, and global styles.
- `src/pages` owns route-level composition grouped by route domain.
- `src/widgets` owns reusable product sections assembled from features and entities.
- `src/features` owns user interactions and use cases.
- `src/entities` owns domain data access, queries, models, and entity presentation.
- `src/shared` owns domain-independent infrastructure, utilities, routing adapters, i18n, and UI primitives.
- Import entities, features, and widgets through their slice `index.ts`; ESLint rejects deep cross-slice imports.

Avoid committing generated files such as `dist/`, `node_modules/`, `*.tsbuildinfo`, or local `.env` files.

## Copy and i18n

The product contains anime and galgame entries. Keep subject-level wording neutral:

- Prefer `planned`, `in progress`, `completed`, `on hold`, and `dropped` for Library status.
- Avoid anime-only wording such as "watching" for subject-level state.
- Episode-specific controls may use watched language because they refer to anime episodes.
- Keep Chinese, English, and Japanese message keys aligned in the relevant `src/shared/i18n/catalogs/*.ts` catalog.
