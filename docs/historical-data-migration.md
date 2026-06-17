# Historical Data Migration

Use this after Render creates the production PostgreSQL database.

The migration is two steps:

1. Export local PostgreSQL history into `.migration/`.
2. Import that snapshot into Render PostgreSQL using the Render external database URL.

The `.migration/` folder is ignored by Git.

## 1. Export Local History

From the project root:

```powershell
.\.venv\Scripts\python.exe -m scripts.export_postgres_snapshot
```

This uses your local `.env` PostgreSQL settings and creates a folder like:

```text
.migration/postgres_snapshot_20260617_130000
```

The snapshot includes:

- `sp500_symbols`
- `vnx_quotes`
- `delayed_quotes`
- `matched_quote_analysis`

It intentionally does not migrate local `pipeline_health_events`, because those describe the local worker, not the production worker.

## 2. Import Into Render Postgres

In Render, open the `vnx-quote-db` database and copy the external PostgreSQL connection string.

Then run:

```powershell
$env:TARGET_DATABASE_URL="postgresql://..."
.\.venv\Scripts\python.exe -m scripts.import_postgres_snapshot ".migration/postgres_snapshot_YYYYMMDD_HHMMSS"
```

If Render provides a `postgres://` URL, the script normalizes it for `psycopg2`.

The import creates tables if needed and uses upserts, so rerunning the same snapshot will not duplicate quote history.

## Best Timing

Recommended order:

1. Deploy Render services from `render.yaml`.
2. Confirm the dashboard opens and login works.
3. Pause/suspend the worker briefly if it is already collecting.
4. Run the historical import.
5. Resume the worker.
6. Refresh the dashboard and confirm historical date ranges are visible.

The import can technically run while the worker is active, but pausing the worker avoids unnecessary contention during the first migration.
