# Live Raw Pipeline

## Purpose

Use this mode when the product needs raw VNX quotes and raw delayed/reference
quotes collected every 60 seconds, with the matcher running every 5 minutes.

This mode needs the laptop to stay awake during market hours.

## Recommended Settings

```text
BATCH_SIZE=100
COLLECTION_INTERVAL_SECONDS=60
COLLECTION_CADENCE_WARNING_SECONDS=120
MATCHER_INTERVAL_SECONDS=300
MATCHER_VALID_WINDOW_SECONDS=60
MATCHER_LOOKBACK_HOURS=24
MATCHER_DELAYED_PADDING_SECONDS=900
VNX_STALE_AFTER_SECONDS=300
DELAYED_STALE_AFTER_SECONDS=1500
SAVE_CSV_BACKUP=false
HEALTH_HEARTBEAT_INTERVAL_SECONDS=300
RAW_RETENTION_DAYS=0
MATCHED_RETENTION_DAYS=0
RETENTION_INTERVAL_SECONDS=3600
```

## Laptop Setup: Local Raw, Neon Matched

Use this setup when the laptop is the market-hours worker:

```text
DATABASE_URL=postgresql://postgres:local_password@localhost:5432/vnx_quote_accuracy
MATCHED_REPLICA_DATABASE_URL=postgresql://neon_user:neon_password@neon_host/neondb?sslmode=require
SAVE_CSV_BACKUP=false
RAW_RETENTION_DAYS=0
MATCHED_RETENTION_DAYS=0
```

With this setup:

- local PostgreSQL stores raw VNX quotes
- local PostgreSQL stores raw delayed quotes
- local PostgreSQL stores matched quote analysis
- Neon stores matched quote analysis only
- Streamlit Cloud reads Neon and updates for your boss

Set `RAW_RETENTION_DAYS=0` if you want to keep all raw data on the laptop while
you are away. Make sure the laptop has enough disk space.

## Command

Check setup first:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_laptop_worker_setup
```

Then start the market worker:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_market_pipeline
```

The live worker does this loop:

```text
1. Check Eastern market hours.
2. If market is open, collect raw VNX quotes for all active symbols.
3. Collect raw delayed/reference quotes for all active symbols.
4. Insert raw rows into PostgreSQL.
5. Record per-symbol snapshot coverage for each feed and polling cycle.
6. Mirror lightweight collector coverage summaries to Neon for Streamlit Cloud.
7. Every 5 minutes, match unmatched VNX rows from PostgreSQL raw tables.
8. Insert matched analysis rows into PostgreSQL.
9. If MATCHED_REPLICA_DATABASE_URL is set, sync matched rows to Neon.
10. Every hour, prune old raw rows using RAW_RETENTION_DAYS.

Snapshot coverage is intentionally separate from raw quote storage. Raw quote
tables are unique by source timestamp, so repeated stale API responses update
the existing raw row instead of creating a new polling-attempt row. The
`quote_snapshot_audit` table records every requested symbol per cycle, which is
the evidence needed to prove whether the API returned all S&P 500 symbols every
60 seconds.
```

The coverage summary sent to Neon is intentionally lightweight. Streamlit Cloud
uses it to show latest requested/returned/missing counts by feed, problem
symbols by reason, actual polling cadence, late cadence gaps beyond
`COLLECTION_CADENCE_WARNING_SECONDS`, and repeated missing symbols. Full
per-symbol audit rows stay in local PostgreSQL unless the storage policy
changes.

The collector sleeps for `COLLECTION_INTERVAL_SECONDS` after a polling cycle
finishes. The observed cycle gap is therefore collection runtime plus the sleep
interval. `COLLECTION_CADENCE_WARNING_SECONDS` is the practical tolerance used
by Streamlit before marking a gap as late.

Returned rows are not automatically treated as fresh. The collector marks rows
as `stale_timestamp` when VNX timestamps are older than
`VNX_STALE_AFTER_SECONDS` or delayed/reference timestamps are older than
`DELAYED_STALE_AFTER_SECONDS`.

Accuracy metrics remain timestamp-windowed. The dashboard uses cents thresholds
of 20, 50, and 70 cents, plus normalized basis-point percentiles, so price
accuracy is not mixed with market movement from wide timestamp gaps.

The matcher reprocesses recent unmatched rows and previous invalid/wide matches
inside `MATCHER_LOOKBACK_HOURS`. This is required because delayed/reference
quotes may arrive after the first matcher pass. A row that was invalid early can
become valid later when the reference timestamp catches up.

To repair existing invalid/wide rows after delayed/reference data arrives:

```powershell
.\.venv\Scripts\python.exe -m scripts.rematch_invalid_matches --lookback-hours 336
.\.venv\Scripts\python.exe -m scripts.rematch_invalid_matches --lookback-hours 336 --apply --sync-replica
```

The first command previews candidate rows. The second writes improved matches
locally and to Neon when `MATCHED_REPLICA_DATABASE_URL` is set.

## Storage Policy

For the vacation data-capture period, keep matched history and raw history.

Recommended vacation posture:

- `RAW_RETENTION_DAYS=0`
- `MATCHED_RETENTION_DAYS=0`

That keeps all raw quote evidence locally while preserving matched quote
analysis locally and in Neon.

## Operating Notes

- Keep the laptop plugged in.
- Disable sleep while plugged in.
- Keep Wi-Fi connected.
- Leave the PowerShell window running.
- Streamlit Cloud should use Neon as `DATABASE_URL`.

If the laptop is off, asleep, or disconnected, collection stops. Existing local
and Neon data remain safe.
