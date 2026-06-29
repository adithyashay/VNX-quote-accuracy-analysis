# VNX Quote Accuracy Analysis

## Project Overview

This project measures VNX quote accuracy against delayed/reference quote prices.

The current production plan is laptop-worker first:

```text
ViaNexus APIs
    ->
Laptop market pipeline during trading hours
    ->
Local PostgreSQL raw VNX + raw delayed + matched analysis
    ->
Neon PostgreSQL matched analysis only
    ->
Streamlit Cloud dashboard
```

This keeps complete raw evidence on the laptop for later analysis while keeping
the cloud database small enough for dashboard access.

## Data Flow

```text
1. Collect raw VNX quotes every 60 seconds.
2. Collect raw delayed/reference quotes every 60 seconds.
3. Store both raw feeds in local PostgreSQL.
4. Run the PostgreSQL matcher every 5 minutes.
5. Store matched analysis in local PostgreSQL.
6. Sync matched analysis only to Neon PostgreSQL.
7. Streamlit Cloud reads Neon so the dashboard is available from anywhere.
```

## Local Setup

Use one project-local virtual environment: `.venv`.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill in `.env` with:

```text
VIANEXUS_API_TOKEN=...
DATABASE_URL=postgresql://postgres:local_password@localhost:5432/vnx_quote_accuracy
MATCHED_REPLICA_DATABASE_URL=postgresql://neon_user:neon_password@neon_host/neondb?sslmode=require
COLLECTION_INTERVAL_SECONDS=60
MATCHER_INTERVAL_SECONDS=300
SAVE_CSV_BACKUP=false
RAW_RETENTION_DAYS=0
MATCHED_RETENTION_DAYS=0
```

`DATABASE_URL` is the local PostgreSQL database. `MATCHED_REPLICA_DATABASE_URL`
is Neon and receives matched rows only.

## Daily Run

Before market open:

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_database
.\.venv\Scripts\python.exe -m scripts.bootstrap_production_database
.\.venv\Scripts\python.exe -m scripts.check_laptop_worker_setup
.\.venv\Scripts\python.exe -m scripts.run_market_pipeline
```

Keep the laptop plugged in, connected to Wi-Fi, and configured not to sleep.

## Dashboard

Local dashboard:

```powershell
.\.venv\Scripts\streamlit.exe run dashboard.py
```

Team dashboard:

```text
Streamlit Cloud -> reads Neon DATABASE_URL
```

The Streamlit Cloud app should use Neon as `DATABASE_URL`, because Neon contains
the matched analysis synced from the laptop worker.

The dashboard is organized around two product questions:

```text
Coverage Monitor: Did VNX and delayed/reference APIs return every expected
S&P 500 symbol on each polling cycle?

Accuracy Monitor: For valid timestamp-matched rows, how far is VNX from the
reference price?
```

Coverage is the first priority. If the API does not return every expected
symbol reliably, the accuracy metrics are incomplete.

The dashboard shows cents difference as the primary accuracy metric:

```text
difference_cents = (vnx_price - delayed_price) * 100
normalized_difference_bps = absolute_percentage_error * 100
```

It also includes basis-point normalization, price-band summaries, and matched
observation counts by ticker and by selected time interval, so the team can see
how many collected snapshots support each view.

Accuracy thresholds use the product-facing cents bands:

```text
20 cents / 50 cents / 70 cents
```

P50/P90/P95/P99 are shown in both cents and basis points. Cents answer the
business question Pedro asked for, while basis points keep high-priced and
low-priced symbols comparable.

The pipeline also records snapshot coverage for every polling cycle:

```text
requested S&P 500 symbols
returned VNX symbols
returned delayed/reference symbols
missing or malformed symbols by feed
```

This is separate from the raw quote tables. Raw quote tables are deduplicated by
source timestamp, while snapshot coverage proves whether each 60-second API poll
returned every requested symbol.

The Streamlit coverage view also derives polling cadence from recent collector
health events. It shows expected cycles, actual cycles, missing cycles, max
cycle gap, latest feed-level coverage, and repeatedly missing/problem symbols.

## Useful Commands

```powershell
.\.venv\Scripts\python.exe -m scripts.run_database_health_check
.\.venv\Scripts\python.exe -m scripts.export_postgres_snapshot
.\.venv\Scripts\python.exe -m scripts.import_postgres_snapshot ".migration\postgres_snapshot_YYYYMMDD_HHMMSS"
```

## Docs

- `docs/live-raw-pipeline.md`: laptop-worker production runbook.
- `docs/historical-data-migration.md`: move matched local history into Neon.
