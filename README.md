# noshiro-db-frontend

The React + TypeScript + Vite frontend for Noshiro DB.

## Stack

- React
- TypeScript
- Vite
- React Router
- ESLint

## Local Development

Configure the local API base in `.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8008
```

Install dependencies:

```bash
npm install
```

Start the frontend:

```bash
npm run dev
```

Default backend API base:

```text
http://127.0.0.1:8008
```

## Checks

```bash
npm run typecheck
npm run lint
npm run build
```

## Source Layout

```text
src/app/       application shell and top-level providers
src/config/    environment configuration
src/features/  business features, feature APIs, query options, and UI modules
src/lib/       framework-agnostic infrastructure such as the API client and query client
src/pages/     route pages
src/routes/    route table and path helpers
src/shared/    shared UI components
src/styles/    global styles
```
