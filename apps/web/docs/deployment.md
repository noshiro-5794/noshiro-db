# Web deployment

The Vite build produces a static SPA. Build with the public site origin and
the public API origin in `.env.production`.

```sh
cp .env.production.example .env.production
pnpm install --frozen-lockfile
pnpm build
```

Set `VITE_SITE_URL` to the frontend origin and `VITE_API_BASE_URL` to the API
origin, such as `https://api.example.org`. The client adds the `/api/v1/`
prefix to resource paths. Set `VITE_HCAPTCHA_SITE_KEY` for an environment
where email verification requires CAPTCHA. Keep the verification secret in
the API environment.

## Serve the app

Publish the contents of `dist/` to the Web host. Serve browser routes through
the SPA fallback and return missing hashed assets as missing files.

```caddyfile
app.example.org {
    root * /srv/noshiro-web

    @assets path /assets/*
    handle @assets {
        file_server
    }

    handle {
        try_files {path} /index.html
        file_server
    }
}
```

Use HTTPS on both origins. Configure API CORS for the frontend origin and
enable credentialed requests for session refresh. Keep refresh cookies secure
and scoped to the API host. Allow the same frontend origin on the API’s
cookie-authenticated refresh and logout endpoints.

Apply a Content Security Policy that permits the Web origin, its configured
API and image origins, and the hCaptcha script and frame origins when used.
Block third-party framing and object embeds. Set the host’s referrer,
permissions, content-type, and HSTS headers. The cache rules in
`public/_headers` cover unversioned icons, the manifest, and the social card.

## Verify a release

Open the home page and a deep link such as `/search`. Verify that the browser
can fetch the API and that authenticated refresh works. Confirm registration
and password reset load the CAPTCHA widget when enabled.

[Backend deployment](../../../deploy/README.md)
