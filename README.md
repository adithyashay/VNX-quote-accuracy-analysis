# VNX Quote Accuracy Analysis

## Current Architecture

The project currently uses a PostgreSQL-backed quote accuracy pipeline.

```text
ViaNexus APIs
    ↓
Batch quote collectors
    ↓
CSV backup + PostgreSQL raw tables
    ↓
VNX-driven timestamp matcher
    ↓
CSV backup + PostgreSQL matched analysis table
    ↓
Streamlit dashboard
```

## Project Overview

The current goal is to analyze how accurate VNX quote prices are compared to delayed/reference quote prices.

The project collects VNX quotes and delayed/reference quotes, matches them by timestamp, calculates percentage error, stores the data in PostgreSQL, and exposes the analysis through a Streamlit dashboard.

---

## Current Working Flow

```text
1. Load S&P 500 symbol universe
2. Collect VNX quotes in batches
3. Collect delayed/reference quotes in batches
4. Save CSV backup files
5. Insert raw VNX and delayed quote data into PostgreSQL
6. Run VNX-driven timestamp matching
7. Save matched data into PostgreSQL
8. Display stats in Streamlit dashboard
```

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill in `.env` with the ViaNexus API token and PostgreSQL connection settings.

## Database Commands

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_database
.\.venv\Scripts\python.exe -m scripts.import_csv_to_postgres
.\.venv\Scripts\python.exe -m scripts.run_database_health_check
```

The health check writes `reports/database_health_report.md` and checks row counts, duplicate key groups, symbol-universe drift, timestamp ranges, and match-validity consistency.

## Dashboard

```powershell
.\.venv\Scripts\streamlit.exe run dashboard.py
```

The dashboard reads from PostgreSQL. Raw CSVs are backup artifacts, not the preferred source for dashboard analysis.

## Automation And Deployment Direction

For production, keep collection and dashboard serving as separate processes:

```text
Trading-hours collector
    -> writes raw + matched data to PostgreSQL
    -> runs on a scheduler/server during market hours

Streamlit dashboard
    -> read-only access to PostgreSQL
    -> deployed for approved viewers
```

Recommended next steps:

1. Run the collector from a scheduler during US market hours.
2. Host PostgreSQL somewhere reachable by both the collector and dashboard.
3. Deploy Streamlit separately with `.env`/secrets configured in the hosting platform.
4. Add basic access control before sharing the dashboard.
