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
npm ci
npm run typecheck
npm run lint
npm run build
```

The production files are generated in `dist/`.

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

React Router handles routes such as `/search`, `/calendar`, and `/subjects/<id>` in the browser. The static server must fall back to `index.html` when a real file does not exist.

In 1Panel, set the static website rewrite or OpenResty config to:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

Without this fallback, direct visits or refreshes on nested routes will return `404 Not Found openresty`.

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
- trusted CSRF origins include `https://noshiro.moe` and `https://api.noshiro.moe`
- CORS allowed origins include `https://noshiro.moe`
- if refresh tokens or session cookies are stored in cookies, cross-subdomain cookies must use `Secure` and `SameSite=None`, or a suitable shared cookie domain such as `.noshiro.moe`
- uploaded media/static backend files have their own serving strategy

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
