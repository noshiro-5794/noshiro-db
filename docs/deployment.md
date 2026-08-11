# Deployment

Noshiro DB Frontend is a Vite single-page application. In production, build it into static files and serve them as a static website. The backend API is deployed separately behind `api.noshiro.moe`.

## Recommended Topology

```text
Browser
  -> https://noshiro.moe/
  -> 1Panel / OpenResty
      -> static frontend files from dist/
  -> https://api.noshiro.moe/
      -> proxied to the Django backend
```

For this project, the recommended production split is:

- frontend: `https://noshiro.moe/`
- backend API: `https://api.noshiro.moe/`
- frontend build variable: `VITE_API_BASE_URL=https://api.noshiro.moe`

The frontend API calls already include `/api/...` in their request paths. Do not set `VITE_API_BASE_URL` to `https://api.noshiro.moe/api` or `/api`, otherwise requests will become `/api/api/...`.

## Production Build

Create a production environment file:

```bash
cp .env.production.example .env.production
```

Set values:

```text
VITE_API_BASE_URL=https://api.noshiro.moe
VITE_HCAPTCHA_SITE_KEY=your-site-key
```

Build:

```bash
fnm use --install-if-missing
corepack enable pnpm
pnpm install --frozen-lockfile
pnpm check
```

The production files are generated in `dist/`.

If dependencies are already installed on the deployment machine, `pnpm build` is enough for a rebuild. Use `pnpm install --frozen-lockfile` for clean release builds.

## 1Panel Static Website

In 1Panel, create a static website for the frontend:

```text
Website type: Static Website
Primary domain: noshiro.moe
HTTPS: enabled
Website directory: the deployed dist/ contents
Default index: index.html
```

The frontend does not need a public Node.js port in production. Do not expose the Vite dev port `5173`.

Copy the built files to the static website directory configured in 1Panel:

```bash
rsync -a --delete dist/ /path/to/1panel/site/root/
```

## SPA Fallback

TanStack Router handles routes such as `/search`, `/calendar`, and `/subjects/<id>` in the browser. The static server must fall back to `index.html` when a real file does not exist.

In 1Panel, set the static website rewrite or OpenResty config to:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}

add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://js.hcaptcha.com https://*.hcaptcha.com; style-src 'self' 'unsafe-inline' https://*.hcaptcha.com; img-src 'self' data: blob: https:; font-src 'self' data:; connect-src 'self' https://api.noshiro.moe https://api.bgm.tv https://*.hcaptcha.com; frame-src https://*.hcaptcha.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

Without this fallback, direct visits or refreshes on nested routes will return `404 Not Found openresty`.

This fallback must apply to all frontend routes, including public pages like `/search`, `/calendar`, `/docs/...`, subject pages, and authenticated workspace routes. API traffic should not be served by the frontend site; it belongs on `api.noshiro.moe`.

## Ports

For public access, only expose HTTPS and HTTP redirect ports:

- `443` for HTTPS
- `80` for HTTP to HTTPS redirect

Keep development and backend process ports private:

- Vite dev server `5173` should not be exposed in production.
- Backend process ports such as `8008` should stay behind the `api.noshiro.moe` reverse proxy.

## Backend Notes

Make sure the backend production settings allow the deployment domain:

- allowed hosts include `api.noshiro.moe`
- CORS allowed origins include only `https://noshiro.moe`, with credentialed requests enabled
- the refresh cookie is host-only for `api.noshiro.moe`, `HttpOnly`, `Secure`, and `SameSite=Lax` or stricter; a shared `.noshiro.moe` cookie domain is unnecessary
- cookie-authenticated refresh and logout endpoints validate `Origin` against an explicit allowlist; CORS response headers and `SameSite` alone are not a substitute for server-side CSRF enforcement
- trusted CSRF origins include `https://noshiro.moe` only for endpoints that actually use Django CSRF validation
- uploaded media/static backend files have their own serving strategy
- calendar cover images may be served from MinIO/CDN URLs when the backend has mirrored them successfully; otherwise Bangumi image URLs can still appear as fallback data

## hCaptcha

Login, registration, and password-reset email-code flows can show hCaptcha before sending a code. Use the public site key in frontend environment variables:

```text
VITE_HCAPTCHA_SITE_KEY=your-site-key
```

The hCaptcha secret belongs only in backend environment variables and must never be committed to this repository.

## Smoke Test

After deployment:

```bash
curl -I https://noshiro.moe/
curl -I https://api.noshiro.moe/api/
```

Then open:

```text
https://noshiro.moe/
https://noshiro.moe/search
https://noshiro.moe/calendar
```

Refresh a nested route such as `/subjects/<id>` to confirm SPA fallback is working.
