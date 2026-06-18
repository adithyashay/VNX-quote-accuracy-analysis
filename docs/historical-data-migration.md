# Historical Data Migration

Use this when Neon needs a backfill of matched history from local PostgreSQL.

The migration is two steps:

1. Export local PostgreSQL history into `.migration/`.
2. Import that snapshot into Neon PostgreSQL using the Neon connection string.

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

The cloud dashboard snapshot includes:

- `sp500_symbols`
- `matched_quote_analysis`

It intentionally does not migrate raw quote tables. Raw VNX and delayed quote
history should stay local on the laptop for detailed analysis.

## 2. Import Into Neon Postgres

In Neon, open the project dashboard and copy the PostgreSQL connection string.

Then run:

```powershell
$env:TARGET_DATABASE_URL="postgresql://..."
.\.venv\Scripts\python.exe -m scripts.import_postgres_snapshot ".migration/postgres_snapshot_YYYYMMDD_HHMMSS"
```

If the provider gives a `postgres://` URL, the script normalizes it for `psycopg2`.

The import creates tables if needed and uses upserts, so rerunning the same snapshot will not duplicate matched quote history.

## Best Timing

Recommended order:

1. Create the Neon database.
2. Confirm the dashboard opens and login works.
3. Stop the laptop worker briefly if it is actively syncing matched rows.
4. Run the historical import.
5. Start the laptop worker again.
6. Refresh the dashboard and confirm historical date ranges are visible.

The import can technically run while the worker is active, but pausing it avoids
unnecessary contention during the first migration.
