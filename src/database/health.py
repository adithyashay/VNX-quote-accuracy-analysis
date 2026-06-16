from pathlib import Path

from src.database.connection import get_connection


REPORTS_DIR = Path("reports")
REPORT_FILE = REPORTS_DIR / "database_health_report.md"


def fetch_one(cursor, query):
    cursor.execute(query)
    row = cursor.fetchone()

    if row is None:
        return None

    return row[0]


def fetch_all(cursor, query):
    cursor.execute(query)
    return cursor.fetchall()


def count_duplicate_groups(cursor, table_name, key_columns):
    key_expression = ", ".join(key_columns)

    return fetch_one(
        cursor,
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT {key_expression}
            FROM {table_name}
            GROUP BY {key_expression}
            HAVING COUNT(*) > 1
        ) duplicate_groups;
        """,
    )


def count_symbols_outside_universe(cursor, table_name):
    return fetch_one(
        cursor,
        f"""
        SELECT COUNT(DISTINCT t.symbol)
        FROM {table_name} t
        LEFT JOIN sp500_symbols s
            ON t.symbol = s.symbol
        WHERE s.symbol IS NULL;
        """,
    )


def get_symbols_outside_universe(cursor, table_name):
    return [
        row[0]
        for row in fetch_all(
            cursor,
            f"""
            SELECT DISTINCT t.symbol
            FROM {table_name} t
            LEFT JOIN sp500_symbols s
                ON t.symbol = s.symbol
            WHERE s.symbol IS NULL
            ORDER BY t.symbol;
            """,
        )
    ]


def get_time_range(cursor, table_name, timestamp_column):
    return fetch_all(
        cursor,
        f"""
        SELECT
            MIN({timestamp_column}),
            MAX({timestamp_column})
        FROM {table_name};
        """,
    )[0]


def get_valid_match_counts(cursor):
    return fetch_all(
        cursor,
        """
        SELECT valid_match, COUNT(*)
        FROM matched_quote_analysis
        GROUP BY valid_match
        ORDER BY valid_match DESC NULLS LAST;
        """,
    )


def get_match_quality_summary(cursor):
    return fetch_all(
        cursor,
        """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(*) FILTER (WHERE time_gap_seconds <= 60) AS rows_within_60s,
            COUNT(*) FILTER (WHERE valid_match IS TRUE) AS valid_rows,
            COUNT(*) FILTER (
                WHERE valid_match IS DISTINCT FROM (time_gap_seconds <= 60)
            ) AS validity_mismatch_rows,
            ROUND(AVG(time_gap_seconds), 4) AS avg_time_gap_seconds,
            ROUND(AVG(absolute_percentage_error), 6) AS avg_abs_error_pct
        FROM matched_quote_analysis;
        """,
    )[0]


def format_count(value):
    if value is None:
        return "0"

    return f"{value:,}"


def format_value(value):
    if value is None:
        return "None"

    return str(value)


def build_markdown_report(results):
    valid_match_rows = "\n".join(
        f"| {format_value(valid_match)} | {format_count(row_count)} |"
        for valid_match, row_count in results["valid_match_counts"]
    )

    drift_rows = "\n".join(
        f"| {table_name} | {', '.join(symbols) if symbols else 'None'} |"
        for table_name, symbols in results["symbols_outside_universe"].items()
    )

    return f"""# Database Health Report

## Table Counts

| Table | Rows |
|---|---:|
| sp500_symbols | {format_count(results["sp500_symbols"])} |
| vnx_quotes | {format_count(results["vnx_quotes"])} |
| delayed_quotes | {format_count(results["delayed_quotes"])} |
| matched_quote_analysis | {format_count(results["matched_quote_analysis"])} |

## Duplicate Key Groups

| Table | Key | Duplicate Groups |
|---|---|---:|
| vnx_quotes | symbol, timestamp_readable | {format_count(results["vnx_duplicate_groups"])} |
| delayed_quotes | symbol, delayed_time_readable | {format_count(results["delayed_duplicate_groups"])} |
| matched_quote_analysis | symbol, vnx_time | {format_count(results["matched_duplicate_groups"])} |

## Symbol Universe Drift

| Table | Symbols Outside sp500_symbols |
|---|---:|
| vnx_quotes | {format_count(results["vnx_symbols_outside_universe"])} |
| delayed_quotes | {format_count(results["delayed_symbols_outside_universe"])} |
| matched_quote_analysis | {format_count(results["matched_symbols_outside_universe"])} |

| Table | Outside Symbols |
|---|---|
{drift_rows}

## Time Ranges

| Dataset | Earliest Timestamp | Latest Timestamp |
|---|---|---|
| VNX Quotes | {results["vnx_time_range"][0]} | {results["vnx_time_range"][1]} |
| Delayed Quotes | {results["delayed_time_range"][0]} | {results["delayed_time_range"][1]} |
| Matched Analysis | {results["matched_time_range"][0]} | {results["matched_time_range"][1]} |

## Match Quality

| Metric | Value |
|---|---:|
| Total matched rows | {format_count(results["match_quality"][0])} |
| Rows with time gap <= 60s | {format_count(results["match_quality"][1])} |
| Rows marked valid | {format_count(results["match_quality"][2])} |
| Validity mismatch rows | {format_count(results["match_quality"][3])} |
| Average time gap seconds | {format_value(results["match_quality"][4])} |
| Average absolute error % | {format_value(results["match_quality"][5])} |

## Valid Match Counts

| valid_match | Rows |
|---|---:|
{valid_match_rows}
"""


def generate_database_health_report():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            results = {
                "sp500_symbols": fetch_one(cursor, "SELECT COUNT(*) FROM sp500_symbols;"),
                "vnx_quotes": fetch_one(cursor, "SELECT COUNT(*) FROM vnx_quotes;"),
                "delayed_quotes": fetch_one(cursor, "SELECT COUNT(*) FROM delayed_quotes;"),
                "matched_quote_analysis": fetch_one(
                    cursor,
                    "SELECT COUNT(*) FROM matched_quote_analysis;",
                ),
                "vnx_duplicate_groups": count_duplicate_groups(
                    cursor,
                    "vnx_quotes",
                    ["symbol", "timestamp_readable"],
                ),
                "delayed_duplicate_groups": count_duplicate_groups(
                    cursor,
                    "delayed_quotes",
                    ["symbol", "delayed_time_readable"],
                ),
                "matched_duplicate_groups": count_duplicate_groups(
                    cursor,
                    "matched_quote_analysis",
                    ["symbol", "vnx_time"],
                ),
                "vnx_symbols_outside_universe": count_symbols_outside_universe(
                    cursor,
                    "vnx_quotes",
                ),
                "delayed_symbols_outside_universe": count_symbols_outside_universe(
                    cursor,
                    "delayed_quotes",
                ),
                "matched_symbols_outside_universe": count_symbols_outside_universe(
                    cursor,
                    "matched_quote_analysis",
                ),
                "symbols_outside_universe": {
                    "vnx_quotes": get_symbols_outside_universe(cursor, "vnx_quotes"),
                    "delayed_quotes": get_symbols_outside_universe(
                        cursor,
                        "delayed_quotes",
                    ),
                    "matched_quote_analysis": get_symbols_outside_universe(
                        cursor,
                        "matched_quote_analysis",
                    ),
                },
                "vnx_time_range": get_time_range(
                    cursor,
                    "vnx_quotes",
                    "timestamp_readable",
                ),
                "delayed_time_range": get_time_range(
                    cursor,
                    "delayed_quotes",
                    "delayed_time_readable",
                ),
                "matched_time_range": get_time_range(
                    cursor,
                    "matched_quote_analysis",
                    "vnx_time",
                ),
                "match_quality": get_match_quality_summary(cursor),
                "valid_match_counts": get_valid_match_counts(cursor),
            }

    report = build_markdown_report(results)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(report, encoding="utf-8")

    print("Database health report saved to:", REPORT_FILE)
    print("Matched duplicate groups:", results["matched_duplicate_groups"])
    print("Validity mismatch rows:", results["match_quality"][3])

    return REPORT_FILE
