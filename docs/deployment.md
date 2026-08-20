# Deployment

Noshiro DB Frontend is a Vite single-page application. In production, build it into static files and serve them through a static web server or object storage/CDN. The backend API is deployed separately behind its own hostname.

## Recommended Topology

```text
Browser
  -> https://<frontend-domain>/
  -> Nginx or equivalent static hosting
      -> static frontend files from dist/
  -> https://<api-domain>/
      -> proxied to the Django backend
```

Use two separate hostnames:

- frontend: `https://<frontend-domain>/`
- backend API: `https://<api-domain>/`
- frontend build variable: `VITE_API_BASE_URL=https://<api-domain>`

The frontend request paths already include `/api/v1/`. Do not set `VITE_API_BASE_URL` to `https://<api-domain>/api` or `https://<api-domain>/api/v1`, otherwise requests become double-prefixed.

## Production Build

Create a production environment file:

```bash
cp .env.production.example .env.production
```

Set values:

```text
VITE_SITE_URL=https://<frontend-domain>
VITE_API_BASE_URL=https://<api-domain>
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

## Static Hosting

Configure any static-site host, Nginx server block, or CDN bucket with:

```text
Document root: contents of dist/
Default index: index.html
HTTPS: enabled
```

The frontend does not need a public Node.js port in production. Do not expose the Vite dev port `5173`.

Copy the built files to your static-site root with a tool that supports atomic or clean replacement, for example:

```bash
rsync -a --delete dist/ /srv/<frontend-domain>/public/
```

Keep the target path under your deployment directory and avoid committing machine-specific paths to this repository.

## SPA Fallback

TanStack Router handles routes such as `/search`, `/calendar`, and `/entities/<id>` in the browser. The static server must fall back to `index.html` when a real file does not exist.

Use a static-site rewrite or Nginx location:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}

add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://js.hcaptcha.com https://*.hcaptcha.com; style-src 'self' 'unsafe-inline' https://*.hcaptcha.com; img-src 'self' data: blob: https:; font-src 'self' data:; connect-src 'self' https://<api-domain> https://api.bgm.tv https://*.hcaptcha.com; frame-src https://*.hcaptcha.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

Replace `<api-domain>` with your actual API hostname and keep the CSP tightly scoped.

Without this fallback, direct visits or refreshes on nested routes will return `404 Not Found`.

This fallback must apply to all frontend routes, including public pages like `/search`, `/calendar`, `/docs/...`, entity pages, and authenticated workspace routes. API traffic should not be served by the frontend site; it belongs on `<api-domain>`.

## Ports

For public access, only expose HTTPS and HTTP redirect ports:

- `443` for HTTPS
- `80` for HTTP to HTTPS redirect

Keep development and backend process ports private:

- Vite dev server `5173` should not be exposed in production.
- Backend process ports such as `8008` should stay behind the API reverse proxy.

## Backend Notes

Make sure the backend production settings allow only the deployment origins:

- allowed hosts include `<api-domain>`
- CORS allowed origins include only `https://<frontend-domain>`, with credentialed requests enabled
- the refresh cookie is host-only for `<api-domain>`, `HttpOnly`, `Secure`, and `SameSite=Lax` or stricter; a shared parent-domain cookie is unnecessary
- cookie-authenticated refresh and logout endpoints validate `Origin` against an explicit allowlist; CORS response headers and `SameSite` alone are not a substitute for server-side CSRF enforcement
- trusted CSRF origins include `https://<frontend-domain>` only for endpoints that actually use Django CSRF validation
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
curl -I https://<frontend-domain>/
curl -I https://<api-domain>/api/v1/
```

Then open:

```text
https://<frontend-domain>/
https://<frontend-domain>/search
https://<frontend-domain>/calendar
```

Refresh a nested route such as `/entities/<id>` to confirm SPA fallback is working.
