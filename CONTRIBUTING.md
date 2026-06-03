# Contributing

Noshiro DB Frontend is a React, TypeScript, and Vite application for the Noshiro DB project.

## Local Setup

```bash
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

## Project Boundaries

- `src/app` owns providers, app shell, and global layout.
- `src/features` owns domain modules, API wrappers, query options, and feature components.
- `src/lib` owns technical infrastructure such as the API client and query client.
- `src/pages` owns route-level composition.
- `src/shared/ui` owns reusable UI primitives without domain ownership.

Avoid committing generated files such as `dist/`, `node_modules/`, `*.tsbuildinfo`, or local `.env` files.
