# Free Deployment Guide

## Target Setup

Use a fully free stack:

- Streamlit Community Cloud hosts the dashboard.
- Neon Free Postgres stores symbols, matched quote analysis, and health events.
- GitHub Actions runs the quote pipeline every 15 minutes during the broad US market-hours window.

The scheduled pipeline stores matched rows only. It does not store raw VNX or delayed quote history in the cloud database.

## Required Accounts

- GitHub account with this private repo
- Streamlit Community Cloud account
- Neon account

## Neon Setup

1. Create a Neon Free Postgres project.
2. Copy the connection string.
3. Use that value as `DATABASE_URL` in GitHub Actions secrets and Streamlit secrets.

## GitHub Actions Secrets

Add these repository secrets:

```text
DATABASE_URL
VIANEXUS_API_TOKEN
```

The workflow is:

```text
.github/workflows/scheduled-matched-pipeline.yml
```

It runs every 15 minutes from `13:00` to `21:59` UTC on weekdays. The Python code also checks Eastern market hours, so extra scheduled runs outside market hours exit without collecting.

## Streamlit Community Cloud Setup

Deploy `dashboard.py` from this private GitHub repo.

Add these Streamlit secrets:

```text
DATABASE_URL="postgresql://..."
DASHBOARD_AUTH_ENABLED="true"
DASHBOARD_USERNAME="your_username"
DASHBOARD_PASSWORD="your_password"
COLLECTION_INTERVAL_SECONDS="900"
MATCHER_INTERVAL_SECONDS="900"
```

Invite your boss as a viewer or share the app URL plus dashboard credentials.

## Historical Data

Use `docs/historical-data-migration.md` to migrate `sp500_symbols` and `matched_quote_analysis` into Neon.

Do not migrate raw quote history for the free deployment. The free database storage budget is limited, and the dashboard analysis is based on matched rows.

## Boss Access Message

Send the URL and username first:

```text
Hi [Name], the VNX Quote Accuracy Dashboard is live here:

[Streamlit app URL]

Username: [username]

I will send the password separately. The dashboard shows quote accuracy, data freshness, and symbol-level analysis.
```

Send the password separately.
