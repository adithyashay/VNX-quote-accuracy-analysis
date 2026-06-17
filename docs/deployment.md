# Deployment Guide

## Target Setup

Use Render for the first production deployment:

- Render Postgres stores quote data and dashboard analysis.
- Render Background Worker runs `python -m scripts.run_market_pipeline`.
- Render Web Service runs Streamlit from `dashboard.py`.
- Dashboard access is protected by `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD`.

The worker runs continuously in the cloud. The code checks Eastern market hours internally, so nobody needs to manually start it each trading day.

## Render Blueprint

The repo includes `render.yaml` with:

- `vnx-quote-db`: managed PostgreSQL database
- `vnx-quote-dashboard`: Streamlit web dashboard
- `vnx-quote-worker`: trading-hours collector and matcher

Both services run:

```bash
python -m scripts.bootstrap_production_database
```

before startup. This creates tables and imports `config/sp500_symbols.csv`.

## Required Secrets

Render will prompt for these values because they are marked `sync: false`:

```text
VIANEXUS_API_TOKEN
DASHBOARD_USERNAME
DASHBOARD_PASSWORD
```

Use a strong dashboard password and share it only with approved users.

## Deploy Steps

1. Open Render and create a new Blueprint from the private GitHub repo.
2. Select `render.yaml`.
3. Enter the required secrets.
4. Deploy the database, dashboard, and worker.
5. Open the dashboard URL.
6. Log in with `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD`.
7. Check the dashboard health panel for raw VNX age, matched age, and worker status.

## Data Migration Note

The cloud database starts with tables and symbols only. Existing local PostgreSQL quote history will not appear in the cloud unless we do a one-time migration.

Two valid options:

- Start fresh in production and let the worker collect new data going forward.
- Export local PostgreSQL data and restore/import it into Render Postgres before sharing the dashboard.

## Production Settings

Current worker settings in `render.yaml`:

```text
BATCH_SIZE=100
COLLECTION_INTERVAL_SECONDS=60
MATCHER_INTERVAL_SECONDS=300
MATCHER_VALID_WINDOW_SECONDS=60
SAVE_CSV_BACKUP=false
HEALTH_HEARTBEAT_INTERVAL_SECONDS=300
```

`SAVE_CSV_BACKUP=false` is intentional in the cloud because PostgreSQL is the source of truth.
