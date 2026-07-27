# Noshiro DB Frontend

Modern React frontend for **Noshiro DB**, a personal anime and galgame database with public discovery, personal records, Markdown reviews, collections, lightweight community activity, admin sync tooling, and subject knowledge graphs.

## Stack

- React 19
- TypeScript
- Vite
- pnpm 11
- TanStack Router
- TanStack Query
- Tailwind CSS v4
- Radix UI primitives
- hCaptcha protected email-code flows

## Features

- Public Home, Search, Calendar, Subject, Subject Graph, and Docs pages
- Password login, email-code login, registration, and password reset flows
- Authenticated workspace shell with profile, settings, notifications, bookmarks, and community pages
- Library management with neutral status labels, ratings, tags, progress, filtering, sorting, and pagination
- Collections with cover presentation, Library-based item adding, horizontal item ordering, and drag sorting
- Subject detail pages with staff, episodes, characters, relations, Bangumi links, public reviews, and personal marks
- Markdown review editor and viewer with GFM rendering and sanitized output
- Lightweight community features around posts, comments, reactions, follows, notifications, bookmarks, reviews, and collections
- Admin panel for backend sync and index maintenance
- Three-language UI foundation: Chinese, English, and Japanese

## Public and Authenticated Scope

Public users can browse:

- Home
- Search
- Calendar
- Subject detail
- Subject knowledge graph
- Docs

Signed-in users can additionally access:

- Workspace Home
- Profile and public profile
- Settings
- Library
- Collections
- Reviews
- Bookmarks
- Notifications
- Activity/community pages
- Admin pages when the backend role allows it

## Getting Started

```bash
fnm use --install-if-missing
corepack enable pnpm
pnpm install --frozen-lockfile
cp .env.example .env
pnpm dev
```

This project targets Node.js 24 LTS. The exact pnpm release is pinned in `package.json`. Local development reaches the deployed API through Vite's same-origin proxy:

```text
API_PROXY_TARGET=https://api.noshiro.moe
VITE_API_BASE_URL=
```

Change `API_PROXY_TARGET` to `http://127.0.0.1:8008` only when developing against a local backend. Production builds do not use this proxy and continue to call `https://api.noshiro.moe` directly.

If hCaptcha is enabled in the backend, set:

```text
VITE_HCAPTCHA_SITE_KEY=your-site-key
```

For remote development over SSH, expose Vite explicitly:

```bash
pnpm dev --host 0.0.0.0
```

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

## Structure

```text
src/app/       application bootstrap, providers, router, shell, and global styles
src/pages/     route-level composition grouped by route domain
src/widgets/   reusable product sections
src/features/  user interactions and use cases
src/entities/  domain data, queries, models, and entity UI
src/shared/    infrastructure, routing adapters, i18n, utilities, and UI primitives
```

Dependencies follow `app -> pages -> widgets -> features -> entities -> shared`. ESLint enforces layer boundaries and
slice public APIs; see the architecture guide for ownership details.

## Documentation

- [Architecture](docs/architecture.md)
- [Development](docs/development.md)
- [Deployment](docs/deployment.md)

## Deployment Notes

The frontend is a static Vite SPA. Production deployment serves `dist/` from `https://noshiro.moe/`, while the backend API is expected at `https://api.noshiro.moe`.

Set production API base without an extra `/api` suffix:

```text
VITE_API_BASE_URL=https://api.noshiro.moe
```

The static server must fall back nested routes to `index.html`; otherwise refreshing routes like `/search`, `/calendar`, or `/subjects/<id>` returns an OpenResty 404.

## Quality Gates

Run before committing:

```bash
pnpm check
```

## Related Repository

Backend API: [noshiro-db-backend](https://github.com/noshiro-5794/noshiro-db-backend)
