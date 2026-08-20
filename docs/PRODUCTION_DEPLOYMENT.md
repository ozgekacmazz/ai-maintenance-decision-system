# Production deployment

Sprint 21C provides a production-like, single-host Compose contract. It does not deploy a real domain or certificate. TLS terminates at a deployment-platform load balancer/reverse proxy in front of this stack; only then should trusted proxy recognition, secure cookies, HTTPS redirect and HSTS be enabled. The upstream must overwrite `X-Forwarded-Proto`, and firewall rules must prevent clients bypassing it to reach this proxy directly. Nginx accepts only the exact `https` value and otherwise substitutes its own scheme.

## Architecture

`proxy:8080` is the only published service. It serves the immutable Vite build and forwards `/api/` to the internal Gunicorn service. Backend and PostgreSQL have no host port. PostgreSQL uses a persistent named volume; model artefacts and prepared metadata/data are read-only bind mounts. Backend and proxy run non-root, with read-only roots, explicit `/tmp`, all capabilities dropped, `no-new-privileges` and an init process.

Images are multi-stage and pinned to Python 3.12.12 slim Bookworm, Node 22.22.0 Alpine, Nginx 1.28.2 Alpine and PostgreSQL 17.7 Alpine. Backend runtime contains Gunicorn 26.1.0 and production requirements, not pytest/Ruff or a compiler. Frontend runtime contains only Nginx and `dist`; source maps are not produced. Build-time `VITE_API_BASE_URL` is empty so the same-origin `/api` contract works behind the proxy.

## Release sequence

1. Copy `.env.production.example` to an ignored secret source and replace every placeholder.
2. Verify the model/data files named by `compose.production.yaml` exist.
3. `docker compose -p <project> -f compose.production.yaml build --no-cache`
4. `docker compose -p <project> -f compose.production.yaml up -d db`
5. `docker compose -p <project> -f compose.production.yaml run --rm migrate`
6. `docker compose -p <project> -f compose.production.yaml up -d --wait backend proxy`
7. Verify `/proxy-health` and `/api/saglik/`.

Migration is an explicit, idempotent one-shot release step; it is never embedded in every Gunicorn replica command. Run only one migrate job per release. A failure blocks backend readiness. Do not use `--fake` or automated destructive rollback. Roll back the application image only after confirming schema compatibility; otherwise restore a verified backup into a new database.

`seed-demo` is excluded from normal startup. For an approved demo environment only, provide demo credentials and run `docker compose -p <project> -f compose.production.yaml --profile demo run --rm seed-demo`. Its production guard is explicitly enabled only inside that profile.

## Proxy and security policy

- SPA fallback applies outside `/api/`; API 404 responses remain JSON.
- Hashed `/assets/` responses cache for one year with `immutable`; HTML is `no-cache`; API responses are `no-store`.
- Gzip is enabled for text/CSS/JSON/JavaScript/SVG; request bodies are capped at 1 MiB and API timeouts are 120 seconds.
- Enforced SPA CSP has no `unsafe-eval` or `unsafe-inline`. Camera, microphone, geolocation, payment and USB are disabled through Permissions-Policy.
- Login alone is limited per edge-observed IP to 5 requests/minute with burst 3. Rejection is JSON 429 with `Retry-After: 60`. This is edge abuse resistance, not account lockout.
- Docs/schema default disabled in production. When explicitly enabled they remain authenticated Django endpoints and must receive a separately tested CSP if exposed through a browser.
- HSTS preload remains opt-in. Enable proxy SSL recognition only when the backend cannot be reached except through the trusted proxy.

Production orchestration owns TLS, encrypted secret delivery, resource limits, log retention and off-host backup retention. Rotate Django/DB secrets through the platform secret store, restart the affected services and revoke old values; never put them in Compose arguments, image layers or shell history.
