import pandas as pd
from psycopg2.extras import execute_values

from src.database.connection import get_connection


def clean_datetime(value):
    """
    Convert pandas/numpy datetime values into Python datetime objects.
    """

    if value is None or pd.isna(value):
        return None

    value = pd.to_datetime(value, errors="coerce")

    if pd.isna(value):
        return None

    return value.to_pydatetime()


def clean_number(value):
    """
    Convert numeric values safely.
    """

    if value is None or pd.isna(value):
        return None

    return float(value)


def clean_bool(value):
    """
    Convert common boolean representations without treating "False" as true.
    """

    if value is None or pd.isna(value):
        return None

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()

    if normalized in {"true", "1", "yes", "y"}:
        return True

    if normalized in {"false", "0", "no", "n"}:
        return False

    return None


def insert_vnx_quote_rows(rows):
    """
    Insert raw VNX quote rows into PostgreSQL.

    Expected row fields:
    symbol, vnx_price, timestamp_readable, collected_at
    """

    if not rows:
        return 0

    cleaned_rows = []

    for row in rows:
        cleaned_rows.append(
            (
                str(row.get("symbol", "")).strip(),
                clean_number(row.get("vnx_price")),
                clean_datetime(row.get("timestamp_readable")),
                clean_datetime(row.get("collected_at")),
            )
        )

    cleaned_rows = [
        row for row in cleaned_rows
        if row[0] and row[2] is not None
    ]

    if not cleaned_rows:
        return 0

    query = """
        INSERT INTO vnx_quotes (
            symbol,
            vnx_price,
            timestamp_readable,
            collected_at
        )
        VALUES %s
        ON CONFLICT (symbol, timestamp_readable)
        DO UPDATE SET
            vnx_price = EXCLUDED.vnx_price,
            collected_at = EXCLUDED.collected_at;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            execute_values(cursor, query, cleaned_rows)
        connection.commit()

    return len(cleaned_rows)


def insert_delayed_quote_rows(rows):
    """
    Insert raw delayed/reference quote rows into PostgreSQL.

    Expected row fields:
    symbol, delayed_price, delayed_time_readable, collected_at
    """

    if not rows:
        return 0

    cleaned_rows = []

    for row in rows:
        cleaned_rows.append(
            (
                str(row.get("symbol", "")).strip(),
                clean_number(row.get("delayed_price")),
                clean_datetime(row.get("delayed_time_readable")),
                clean_datetime(row.get("collected_at")),
            )
        )

    cleaned_rows = [
        row for row in cleaned_rows
        if row[0] and row[2] is not None
    ]

    if not cleaned_rows:
        return 0

    query = """
        INSERT INTO delayed_quotes (
            symbol,
            delayed_price,
            delayed_time_readable,
            collected_at
        )
        VALUES %s
        ON CONFLICT (symbol, delayed_time_readable)
        DO UPDATE SET
            delayed_price = EXCLUDED.delayed_price,
            collected_at = EXCLUDED.collected_at;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            execute_values(cursor, query, cleaned_rows)
        connection.commit()

    return len(cleaned_rows)


def insert_matched_quote_rows(rows):
    """
    Insert matched quote analysis rows into PostgreSQL.

    Expected row fields:
    symbol, vnx_price, vnx_time, delayed_price, delayed_time,
    time_gap_seconds, valid_match, difference, percentage_error,
    absolute_percentage_error
    """

    if rows is None:
        return 0

    if isinstance(rows, pd.DataFrame):
        rows = rows.to_dict("records")

    if not rows:
        return 0

    cleaned_rows = []

    for row in rows:
        cleaned_rows.append(
            (
                str(row.get("symbol", "")).strip(),
                clean_number(row.get("vnx_price")),
                clean_datetime(row.get("vnx_time")),
                clean_number(row.get("delayed_price")),
                clean_datetime(row.get("delayed_time")),
                clean_number(row.get("time_gap_seconds")),
                clean_bool(row.get("valid_match")),
                clean_number(row.get("difference")),
                clean_number(row.get("percentage_error")),
                clean_number(row.get("absolute_percentage_error")),
            )
        )

    cleaned_rows = [
        row for row in cleaned_rows
        if row[0] and row[2] is not None
    ]

    if not cleaned_rows:
        return 0

    query = """
        INSERT INTO matched_quote_analysis (
            symbol,
            vnx_price,
            vnx_time,
            delayed_price,
            delayed_time,
            time_gap_seconds,
            valid_match,
            difference,
            percentage_error,
            absolute_percentage_error
        )
        VALUES %s
        ON CONFLICT (symbol, vnx_time)
        DO UPDATE SET
            vnx_price = EXCLUDED.vnx_price,
            delayed_price = EXCLUDED.delayed_price,
            delayed_time = EXCLUDED.delayed_time,
            time_gap_seconds = EXCLUDED.time_gap_seconds,
            valid_match = EXCLUDED.valid_match,
            difference = EXCLUDED.difference,
            percentage_error = EXCLUDED.percentage_error,
            absolute_percentage_error = EXCLUDED.absolute_percentage_error;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            execute_values(cursor, query, cleaned_rows)
        connection.commit()

    return len(cleaned_rows)
