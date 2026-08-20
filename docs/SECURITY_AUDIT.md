# Security audit — Sprint 21B

Date: 20 August 2026. Scope: Django/DRF authentication, authorization, inputs, dependencies and production settings plus frontend dependencies. Secret values were not persisted. Findings were validated against installed versions and existing regression tests.

## Findings

| Severity | Evidence and impact | Disposition |
| --- | --- | --- |
| Critical / High | No verified runtime application finding. `npm audit` (production and all dependencies) returned zero vulnerabilities; pip-audit reported no advisory in Django, DRF, SimpleJWT, psycopg or scikit-learn. | No runtime upgrade required. |
| Medium | `pytest` 8.4.2 matched PYSEC-2026-1845; it is development-only and the fixed 9.0.3 release is a major upgrade outside the automatic-upgrade rule. | Documented for a compatibility-tested development-tool upgrade. It is not shipped at runtime. |
| Low | Container pip 25.0.1 matched tooling advisories with fixes in newer pip releases. | Defer to Sprint 21C base-image/tooling refresh; not an application dependency. |
| Medium | Production security settings were absent as a distinct contract. | Added environment-driven production settings: HTTPS redirect, secure cookies, HSTS, nosniff, DENY framing, strict referrer policy and PostgreSQL SSL. Proxy SSL recognition remains explicit opt-in. |
| Medium | Authenticated API responses had no explicit cache prohibition. | All `/api/` responses now send `Cache-Control: no-store` and `Pragma: no-cache`. |
| Medium | Login throttling is not present. | Accepted for this internal role-based scope; deployment edge rate limiting is a Sprint 21C requirement. Credentials and authorization remain authoritative in the backend. |
| Informational | `check --deploy` reports only `security.W021` because HSTS preload defaults false. | Intentional: preload is irreversible/domain-wide and must follow deployment-domain review. The check was not silenced. |

Production schema/docs follow the current authenticated view policy and must be smoke-tested behind the final proxy. CSP and Permissions-Policy are deliberately deferred to Sprint 21C: Swagger uses inline assets and a proxy-level policy must be tested rather than guessed. HSTS is emitted only on HTTPS; `SECURE_PROXY_SSL_HEADER` must be enabled only for a trusted proxy. `SECURE_HSTS_PRELOAD` remains opt-in.

Anonymous company-data endpoints are covered as 401; USER admin CRUD/log/override/user-management paths as 403; ADMIN management as allowed. Existing regressions cover object lookup/permission ordering, strict unexpected fields, read-only snapshots, write-only passwords, IDOR-style UUID attempts, pagination limits (1–100), safe ordering/filter allowlists, path/hash metadata handling, NaN/Infinity rejection, guarded seed and exact-DB E2E reset. JWT access lifetime is 5 minutes, refresh lifetime one day, rotation and blacklist are enabled. Refresh tokens remain HttpOnly cookies and access tokens stay in memory. CORS uses an explicit development allowlist, not wildcard. Trace IDs accept only a bounded safe pattern and production errors do not return stack traces.

Repository searches found no production private key, cloud/API token, committed `.env`, raw JWT or database secret. Demo/test credentials are environment-provided test data, not production secrets. Logs do not intentionally record Authorization, raw password or token values. Absolute developer paths in transient tool output are not repository content.
