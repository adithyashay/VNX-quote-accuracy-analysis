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