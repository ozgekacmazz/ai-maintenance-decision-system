# PostgreSQL backup and restore

Use a protected directory outside the repository. Do not place passwords on the command line; supply them through the container environment/secret mechanism. Restrict backup permissions, encrypt at rest and apply the organisation's off-host retention policy.

Example custom-format backup from the database container:

```sh
docker compose -p <project> -f compose.production.yaml exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/release.dump
```

Copy `/tmp/release.dump` to the protected backup destination, record application/image and migration versions, then remove the container temporary copy. Validate with `pg_restore --list` before restore.

Restore only into a new empty database, never directly over the active production database:

```sh
docker compose -p <project> -f compose.production.yaml exec -T db \
  createdb -U "$POSTGRES_USER" sensor_restore_check
docker compose -p <project> -f compose.production.yaml exec -T db \
  pg_restore -U "$POSTGRES_USER" -d sensor_restore_check --no-owner /tmp/release.dump
```

Confirm migration compatibility and counts/relationships for users, predictions, work orders, replay sessions and replay items. Perform application smoke tests against a separately configured restore stack before traffic cutover. Sprint 21C's isolated rehearsal restored `10` predictions, `4` work orders, `1` replay session, `250` replay items and `5` users, then removed only the exact restore database and temporary dump.
