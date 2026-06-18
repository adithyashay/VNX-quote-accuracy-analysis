# Live Raw Pipeline

## Purpose

Use this mode when the product needs raw VNX quotes and raw delayed/reference
quotes collected every 60 seconds, with the matcher running every 5 minutes.

This mode needs an always-on worker during market hours. It should not run as a
normal GitHub-hosted scheduled workflow, because GitHub schedules have a minimum
5-minute interval and can be delayed or dropped during high load.

## Recommended Settings

```text
BATCH_SIZE=100
COLLECTION_INTERVAL_SECONDS=60
MATCHER_INTERVAL_SECONDS=300
MATCHER_VALID_WINDOW_SECONDS=60
MATCHER_LOOKBACK_HOURS=24
MATCHER_DELAYED_PADDING_SECONDS=900
SAVE_CSV_BACKUP=false
HEALTH_HEARTBEAT_INTERVAL_SECONDS=300
RAW_RETENTION_DAYS=1
MATCHED_RETENTION_DAYS=0
RETENTION_INTERVAL_SECONDS=3600
```

## Command

```powershell
.\.venv\Scripts\python.exe -m scripts.run_market_pipeline
```

The live worker does this loop:

```text
1. Check Eastern market hours.
2. If market is open, collect raw VNX quotes for all active symbols.
3. Collect raw delayed/reference quotes for all active symbols.
4. Insert raw rows into PostgreSQL.
5. Every 5 minutes, match unmatched VNX rows from PostgreSQL raw tables.
6. Insert matched analysis rows into PostgreSQL.
7. Every hour, prune old raw rows using RAW_RETENTION_DAYS.
```

## Storage Policy

Keep matched history long-term and raw history short-term.

Recommended free-tier posture:

- `RAW_RETENTION_DAYS=1`
- `MATCHED_RETENTION_DAYS=0`

That keeps one day of raw quote evidence for debugging while preserving the
matched quote analysis used by the dashboard.

## Deployment Reality

Streamlit Community Cloud can host the dashboard, and Neon can store the data.
The missing piece is the always-on worker.

Options:

- Office or laptop worker: free, but that machine must stay on during market hours.
- Self-hosted GitHub Actions runner: free GitHub orchestration, but still needs an
  always-on machine.
- Paid always-on service: most reliable, but not completely free.

GitHub-hosted Actions are still useful for the matched-only free deployment, but
they are not a reliable 60-second market data worker.
