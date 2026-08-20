# Final runbook

## Delivery procedure

1. Prerequisites: Docker Compose v2, enough disk/RAM, pinned base-image registry access and approved PostgreSQL/model artefacts.
2. Prepare ignored environment values from `.env.production.example`; empty critical values fail fast.
3. Verify binary/failure-type artefacts and metadata plus input-domain and prepared replay files.
4. Build using `docker compose -p <project> -f compose.production.yaml build --no-cache`.
5. Start DB and wait for `pg_isready`.
6. Run exactly one `run --rm migrate`; rerun must report “No migrations to apply.”
7. Start backend and proxy with `up -d --wait`; do not publish backend or DB ports.
8. Check `/proxy-health`, `/api/saglik/`, CSP/Permissions-Policy, HTML/static cache and API no-store.
9. If and only if this is an approved demo, run the explicit `demo` profile seed.
10. Smoke ADMIN and USER login without recording credentials.
11. Keep docs disabled by default; when enabled, verify authenticated schema/docs access.
12. Run contract, axe, real journey, replay and production-smoke Playwright packages.
13. Create and validate a custom-format backup outside the repository.
14. Restore into a new empty database and verify core relationship counts.
15. Inspect stdout/stderr for startup, migration, health, trace correlation and absence of credentials/tokens.
16. Gracefully stop with `docker compose -p <project> -f compose.production.yaml stop`; SIGTERM/SIGQUIT grace periods apply.
17. Rollback: stop traffic, retain DB, select the previous compatible image, and restore only into a new DB when schema compatibility requires it. Never automate destructive rollback.
18. Troubleshooting: failed config means a missing/blank environment value; unhealthy backend means DB/migration/model readiness; 429 means wait for `Retry-After`; CSP errors require a narrowly justified source change.
19. Presentation: follow `DEMO_SCENARIO.md`, say Precision/Recall/PR-AUC—not Accuracy—and describe replay as controlled HTTP batch simulation.
20. Final remote-clone gate: after Sprint 21 is committed and pushed, clone the exact checkpoint into a new directory, verify HEAD, supply fresh test-only secrets, run two clean production builds plus zero-DB smoke, then delete only that clone's exact smoke resources.

No real remote clone can validate uncommitted Sprint 21 content. The current clean-source snapshot rehearsal covers the working tree; the remote clone is the final post-checkpoint delivery gate.
