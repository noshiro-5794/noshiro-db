# Web development

Use Node.js 24 and the project-pinned pnpm version. Start the backend
from the [repository setup](../../../README.md#local-development).

## Local environment

From `apps/web`:

```sh
corepack enable pnpm
pnpm install --frozen-lockfile
cp .env.example .env
pnpm dev
```

`API_PROXY_TARGET` selects the backend origin for Vite. It defaults to
`http://127.0.0.1:8008`. An empty `VITE_API_BASE_URL` keeps API calls on
the development origin. For an explicit remote backend, set
`API_PROXY_TARGET` to its HTTP or HTTPS origin.

The development proxy adapts secure refresh cookies for local HTTP and keeps
the remaining cookie attributes. Production builds use the public API URL.
Set `VITE_HCAPTCHA_SITE_KEY` to the relevant public site key when testing a
backend that requires CAPTCHA.

## Commands

| Command                   | Purpose                                                         |
| ------------------------- | --------------------------------------------------------------- |
| `pnpm dev`                | Start Vite                                                      |
| `pnpm test`               | Run unit tests                                                  |
| `pnpm test:e2e`           | Run browser tests                                               |
| `pnpm check`              | Run formatting, types, lint, tests, dead-code checks, and build |
| `pnpm check:dependencies` | Audit production dependencies                                   |
| `pnpm icons`              | Regenerate platform icons and the social card                   |

Install Chromium with `pnpm exec playwright install chromium`.
Browser tests and asset generation support `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`
for a local Chromium executable. Browser scenarios use mocked API responses.
Start the local backend for live cross-application checks.

Platform icons and the social card are generated from
`public/assets/brand/mark.png` by `tools/generate-icons.mjs`.

## Remote development

When Vite runs on a remote development host, forward its listening port over
SSH. Set the Vite backend target from that host’s perspective. Use
`pnpm dev --host 0.0.0.0` only when a development environment needs access
from another device.
