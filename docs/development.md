# Development

## Requirements

- Node.js 20+
- npm
- A running Noshiro DB backend API

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
