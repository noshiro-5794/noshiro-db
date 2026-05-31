# Noshiro DB Frontend

Modern React frontend for **Noshiro DB**, a personal anime and galgame database for discovery, tracking, library management, reviews, collections, and activity.

## Tech Stack

- React 19
- TypeScript
- Vite
- React Router
- TanStack Query
- Tailwind CSS
- Radix UI primitives
- hCaptcha protected email-code flows

## Features

- Public home page, search, calendar, subject detail, and docs
- Password login and email-code login
- Registration with hCaptcha-protected verification code sending
- Authenticated workspace shell
- Profile editing, avatar upload, and user accent color
- Library, collections, reviews, and tag-based library filtering
- Subject detail actions for marking, rating, comments, deletion, progress, relations, and reviews
- Markdown review rendering foundation

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

## Project Structure

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

See also:

- [Development](docs/development.md)
- [Architecture](docs/architecture.md)

## Quality Checks

Run before committing:

```bash
npm run typecheck
npm run lint
npm run build
```

## Related Repository

Backend API: `noshiro-db-backend`
