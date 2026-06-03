# Noshiro DB Frontend

Modern React frontend for **Noshiro DB**, a personal anime and galgame database with discovery, tracking, reviews, collections, community activity, and subject knowledge graphs.

## Stack

- React 19
- TypeScript
- Vite
- React Router
- TanStack Query
- Tailwind CSS v4
- Radix UI primitives
- hCaptcha protected email-code flows

## Features

- Public Home, Search, Calendar, Subject, Subject Graph, and Docs pages
- Password login, email-code login, registration, and password reset flows
- Authenticated workspace shell with profile, settings, notifications, bookmarks, and community pages
- Library management with status, ratings, tags, progress, filtering, sorting, and pagination
- Collections with cover presentation, Library-based item adding, horizontal item ordering, and drag sorting
- Subject detail pages with staff, episodes, characters, relations, Bangumi links, public reviews, and personal marks
- Markdown review editor and viewer with GFM rendering and sanitized output
- Lightweight community features around posts, comments, reactions, follows, notifications, bookmarks, reviews, and collections
- Admin panel for backend sync and index maintenance
- Three-language UI foundation: Chinese, English, and Japanese

## Getting Started

```bash
npm install
cp .env.example .env
npm run dev
```

Default local API base:

```text
VITE_API_BASE_URL=http://127.0.0.1:8008
```

If hCaptcha is enabled in the backend, set:

```text
VITE_HCAPTCHA_SITE_KEY=your-site-key
```

## Scripts

```bash
npm run dev
npm run typecheck
npm run lint
npm run build
npm run preview
```

## Structure

```text
src/app/       application shell and top-level providers
src/config/    environment configuration
src/features/  domain features, API wrappers, query options, and feature components
src/lib/       API client, query client, and framework-agnostic utilities
src/pages/     route pages
src/routes/    route table and path helpers
src/shared/    shared UI primitives
src/styles/    global styles, theme tokens, and Tailwind utilities
```

## Documentation

- [Architecture](docs/architecture.md)
- [Development](docs/development.md)
- [Deployment](docs/deployment.md)

## Quality Gates

Run before committing:

```bash
npm run typecheck
npm run lint
npm run build
```

## Related Repository

Backend API: `noshiro-db-backend`
