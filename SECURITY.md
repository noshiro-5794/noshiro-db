# Security policy

## Report a vulnerability

Use the repository’s [private vulnerability reporting page](https://github.com/noshiro-5794/noshiro-db/security).
Include the affected component and revision, the conditions needed to reproduce
the issue, and its impact. Keep credentials and private user data out of the
report.

Security fixes target the current `main` branch.

## Operate a release

- Store signing keys, provider credentials, and database credentials outside the checkout.
- Serve the Web and public API through HTTPS. Set explicit CORS origins and trusted proxy addresses.
- Set `JWT_SECRET`, `REFRESH_COOKIE_SECURE`, and `ENABLE_API_DOCS` in the production API environment.
- Restrict database, Redis, and object storage access to the services that need it.
- Pass durable record IDs in Celery messages. Retrieve sensitive data inside the worker.
- Use the authenticated MCP endpoint for public knowledge queries.

See the [deployment guide](deploy/README.md) for the production service layout.
