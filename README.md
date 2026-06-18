# VNX Quote Accuracy Analysis

## Project Overview

This project measures how accurate VNX quote prices are compared to delayed/reference quote prices.

The free cloud deployment stores matched analysis only. Raw VNX and delayed quotes are collected, matched in memory, and discarded after the matched rows are saved. This keeps the database small enough for a free Postgres tier.

```text
ViaNexus APIs
    ->
GitHub Actions scheduled pipeline
    ->
In-memory VNX vs delayed quote matching
    ->
PostgreSQL matched_quote_analysis + health events
    ->
Streamlit dashboard
```

## Working Flow

```text
1. Load S&P 500 symbol universe
2. Collect VNX quotes in batches
3. Collect delayed/reference quotes in batches
4. Match VNX and delayed quotes in memory
5. Save matched quote analysis into PostgreSQL
6. Record scheduled pipeline health events
7. Display stats and data freshness in Streamlit
```

## Local Setup

Use one project-local virtual environment: `.venv`.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill in `.env` with the ViaNexus API token and PostgreSQL connection settings.

Avoid creating a second environment named `venv`; keeping only `.venv` prevents Streamlit from launching with missing packages.

## Local Commands

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_database
.\.venv\Scripts\python.exe -m scripts.bootstrap_production_database
.\.venv\Scripts\python.exe -m scripts.run_scheduled_matched_pipeline
.\.venv\Scripts\python.exe -m scripts.run_market_pipeline
.\.venv\Scripts\python.exe -m scripts.run_database_health_check
```

The health check writes `reports/database_health_report.md` and checks row counts, duplicate key groups, symbol-universe drift, timestamp ranges, match-validity consistency, and latest pipeline health events.

`scripts.run_market_pipeline` is the live raw pipeline. It collects raw VNX and
delayed quotes every 60 seconds and runs the PostgreSQL matcher every 5 minutes.
Use `SAVE_CSV_BACKUP=false` and `RAW_RETENTION_DAYS=1` for a cloud database.

## Dashboard

```powershell
.\.venv\Scripts\streamlit.exe run dashboard.py
```

The dashboard reads from PostgreSQL. The free deployment uses `matched_quote_analysis` as the source of truth.

## Free Deployment

Use this fully free stack:

```text
GitHub Actions
    -> scheduled every 15 minutes during the broad market-hours window
    -> runs matched-only collection/matching

Neon Free Postgres
    -> stores symbols, matched quote analysis, and health events

Streamlit Community Cloud
    -> hosts dashboard for approved viewers
```

Useful scheduled pipeline settings:

```text
BATCH_SIZE=100
COLLECTION_INTERVAL_SECONDS=900
MATCHER_INTERVAL_SECONDS=900
MATCHER_VALID_WINDOW_SECONDS=60
SAVE_CSV_BACKUP=false
HEALTH_HEARTBEAT_INTERVAL_SECONDS=900
MATCHED_RETENTION_DAYS=0
```

Deployment files:

- `.github/workflows/scheduled-matched-pipeline.yml` runs the matched-only pipeline on GitHub Actions.
- `scripts.run_scheduled_matched_pipeline` collects current quotes, matches in memory, and stores matched rows only.
- `docs/free-deployment.md` explains the Streamlit Community Cloud + Neon + GitHub Actions setup.
- `docs/live-raw-pipeline.md` explains the raw 60-second worker mode.
- `docs/historical-data-migration.md` explains how to move local matched quote history into Neon Postgres.
