from pathlib import Path

from src.database.connection import get_connection


REPORTS_DIR = Path("reports")
REPORT_FILE = REPORTS_DIR / "raw_data_coverage_report.md"


def fetch_one(cursor, query):
    """
    Run a SQL query and return the first value from the first row.
    """

    cursor.execute(query)
    result = cursor.fetchone()

    if result is None:
        return None

    return result[0]


def fetch_all(cursor, query):
    """
    Run a SQL query and return all rows.
    """

    cursor.execute(query)
    return cursor.fetchall()


def generate_raw_data_coverage_report():
    """
    Generate a human-readable raw data coverage report from PostgreSQL.
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            total_sp500_symbols = fetch_one(
                cursor,
                "SELECT COUNT(*) FROM sp500_symbols;"
            )

            total_vnx_rows = fetch_one(
                cursor,
                "SELECT COUNT(*) FROM vnx_quotes;"
            )

            total_delayed_rows = fetch_one(
                cursor,
                "SELECT COUNT(*) FROM delayed_quotes;"
            )

            total_matched_rows = fetch_one(
                cursor,
                "SELECT COUNT(*) FROM matched_quote_analysis;"
            )

            symbols_with_vnx = fetch_one(
                cursor,
                "SELECT COUNT(DISTINCT symbol) FROM vnx_quotes;"
            )

            symbols_with_delayed = fetch_one(
                cursor,
                "SELECT COUNT(DISTINCT symbol) FROM delayed_quotes;"
            )

            symbols_with_matched = fetch_one(
                cursor,
                "SELECT COUNT(DISTINCT symbol) FROM matched_quote_analysis;"
            )

            symbols_with_both_raw = fetch_one(
                cursor,
                """
                SELECT COUNT(*)
                FROM sp500_symbols s
                WHERE EXISTS (
                    SELECT 1
                    FROM vnx_quotes v
                    WHERE v.symbol = s.symbol
                )
                AND EXISTS (
                    SELECT 1
                    FROM delayed_quotes d
                    WHERE d.symbol = s.symbol
                );
                """
            )

            vnx_time_range = fetch_all(
                cursor,
                """
                SELECT
                    MIN(timestamp_readable),
                    MAX(timestamp_readable)
                FROM vnx_quotes;
                """
            )[0]

            delayed_time_range = fetch_all(
                cursor,
                """
                SELECT
                    MIN(delayed_time_readable),
                    MAX(delayed_time_readable)
                FROM delayed_quotes;
                """
            )[0]

            matched_time_range = fetch_all(
                cursor,
                """
                SELECT
                    MIN(vnx_time),
                    MAX(vnx_time)
                FROM matched_quote_analysis;
                """
            )[0]

            missing_vnx_symbols = fetch_all(
                cursor,
                """
                SELECT s.symbol
                FROM sp500_symbols s
                LEFT JOIN vnx_quotes v
                    ON s.symbol = v.symbol
                WHERE v.symbol IS NULL
                ORDER BY s.symbol;
                """
            )

            missing_delayed_symbols = fetch_all(
                cursor,
                """
                SELECT s.symbol
                FROM sp500_symbols s
                LEFT JOIN delayed_quotes d
                    ON s.symbol = d.symbol
                WHERE d.symbol IS NULL
                ORDER BY s.symbol;
                """
            )

            top_vnx_symbols = fetch_all(
                cursor,
                """
                SELECT symbol, COUNT(*) AS row_count
                FROM vnx_quotes
                GROUP BY symbol
                ORDER BY row_count DESC
                LIMIT 20;
                """
            )

            top_delayed_symbols = fetch_all(
                cursor,
                """
                SELECT symbol, COUNT(*) AS row_count
                FROM delayed_quotes
                GROUP BY symbol
                ORDER BY row_count DESC
                LIMIT 20;
                """
            )

            vnx_rows_by_symbol_stats = fetch_all(
                cursor,
                """
                SELECT
                    MIN(row_count),
                    MAX(row_count),
                    ROUND(AVG(row_count), 2)
                FROM (
                    SELECT symbol, COUNT(*) AS row_count
                    FROM vnx_quotes
                    GROUP BY symbol
                ) t;
                """
            )[0]

            delayed_rows_by_symbol_stats = fetch_all(
                cursor,
                """
                SELECT
                    MIN(row_count),
                    MAX(row_count),
                    ROUND(AVG(row_count), 2)
                FROM (
                    SELECT symbol, COUNT(*) AS row_count
                    FROM delayed_quotes
                    GROUP BY symbol
                ) t;
                """
            )[0]

    missing_vnx_list = [row[0] for row in missing_vnx_symbols]
    missing_delayed_list = [row[0] for row in missing_delayed_symbols]

    missing_vnx_text = ", ".join(missing_vnx_list) if missing_vnx_list else "None"
    missing_delayed_text = ", ".join(missing_delayed_list) if missing_delayed_list else "None"

    top_vnx_table = "\n".join(
        [f"| {symbol} | {count:,} |" for symbol, count in top_vnx_symbols]
    )

    top_delayed_table = "\n".join(
        [f"| {symbol} | {count:,} |" for symbol, count in top_delayed_symbols]
    )

    report = f"""# Full S&P 500 Raw Data Coverage Report

## Executive Summary

The current PostgreSQL database contains raw VNX quote data, raw delayed/reference quote data, and matched quote analysis data for the S&P 500 universe.

This report summarizes how much raw data has been collected so far, how many S&P 500 symbols have coverage, and the timestamp range of the available data.

---

## Overall Data Summary

| Metric | Value |
|---|---:|
| Total S&P 500 Symbols Loaded | {total_sp500_symbols:,} |
| Total VNX Raw Quote Rows | {total_vnx_rows:,} |
| Total Delayed Raw Quote Rows | {total_delayed_rows:,} |
| Total Matched Analysis Rows | {total_matched_rows:,} |
| Symbols with VNX Data | {symbols_with_vnx:,} |
| Symbols with Delayed Data | {symbols_with_delayed:,} |
| Symbols with Both VNX and Delayed Raw Data | {symbols_with_both_raw:,} |
| Symbols with Matched Analysis Data | {symbols_with_matched:,} |

---

## Raw Data Time Range

| Dataset | Earliest Timestamp | Latest Timestamp |
|---|---|---|
| VNX Quotes | {vnx_time_range[0]} | {vnx_time_range[1]} |
| Delayed Quotes | {delayed_time_range[0]} | {delayed_time_range[1]} |
| Matched Analysis | {matched_time_range[0]} | {matched_time_range[1]} |

---

## Row Distribution by Symbol

| Dataset | Min Rows per Symbol | Max Rows per Symbol | Avg Rows per Symbol |
|---|---:|---:|---:|
| VNX Quotes | {vnx_rows_by_symbol_stats[0]:,} | {vnx_rows_by_symbol_stats[1]:,} | {vnx_rows_by_symbol_stats[2]} |
| Delayed Quotes | {delayed_rows_by_symbol_stats[0]:,} | {delayed_rows_by_symbol_stats[1]:,} | {delayed_rows_by_symbol_stats[2]} |

---

## Missing Data Summary

| Missing Data Type | Count |
|---|---:|
| Symbols Missing VNX Data | {len(missing_vnx_list):,} |
| Symbols Missing Delayed Data | {len(missing_delayed_list):,} |

### Symbols Missing VNX Data

{missing_vnx_text}

### Symbols Missing Delayed Data

{missing_delayed_text}

---

## Top 20 Symbols by VNX Raw Rows

| Symbol | VNX Raw Rows |
|---|---:|
{top_vnx_table}

---

## Top 20 Symbols by Delayed Raw Rows

| Symbol | Delayed Raw Rows |
|---|---:|
{top_delayed_table}

---

## Methodology

The S&P 500 symbol universe is currently loaded from `config/sp500_symbols.csv`.

Raw quote data is currently stored in PostgreSQL in two main tables:

- `vnx_quotes`
- `delayed_quotes`

Matched quote accuracy analysis is stored in:

- `matched_quote_analysis`

The matching logic is VNX-driven. Each VNX quote is treated as the primary observation, and the system finds the closest delayed/reference quote for the same symbol by timestamp.

This report is a raw data coverage report. It measures data availability and coverage, not final quote accuracy.

---

## Notes

CSV files are still maintained as backup/export files, but PostgreSQL is now being used as the main analysis database for larger S&P 500 quote history.
"""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(report, encoding="utf-8")

    print()
    print("Database Raw Data Coverage Report")
    print("=================================")
    print("Total S&P 500 symbols:", f"{total_sp500_symbols:,}")
    print("Total VNX raw rows:", f"{total_vnx_rows:,}")
    print("Total delayed raw rows:", f"{total_delayed_rows:,}")
    print("Total matched analysis rows:", f"{total_matched_rows:,}")
    print("Symbols with both VNX and delayed raw data:", f"{symbols_with_both_raw:,}")
    print()
    print("Saved report to:", REPORT_FILE)

    return REPORT_FILE