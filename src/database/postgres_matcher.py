from datetime import timedelta

import pandas as pd

from src.database.connection import get_connection
from src.matcher import match_vnx_rows_to_delayed, normalize_matched_dataframe


def rows_to_dataframe(cursor, columns):
    rows = cursor.fetchall()

    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows, columns=columns)


def normalize_quote_dataframe(df, time_columns, number_columns):
    if df.empty:
        return df

    normalized_df = df.copy()

    for column in time_columns:
        normalized_df[column] = pd.to_datetime(
            normalized_df[column],
            errors="coerce",
        )

    for column in number_columns:
        normalized_df[column] = pd.to_numeric(
            normalized_df[column],
            errors="coerce",
        )

    return normalized_df.dropna(subset=time_columns)


def load_vnx_rows_to_match(cursor, lookback_hours, valid_window_seconds=60):
    query = """
        SELECT
            v.symbol,
            v.vnx_price,
            v.timestamp_readable
        FROM vnx_quotes v
        LEFT JOIN matched_quote_analysis m
            ON m.symbol = v.symbol
           AND m.vnx_time = v.timestamp_readable
        WHERE v.timestamp_readable >= (
            (CURRENT_TIMESTAMP AT TIME ZONE 'America/New_York')
            - (%s * INTERVAL '1 hour')
        )
        AND (
            m.symbol IS NULL
            OR m.valid_match IS DISTINCT FROM TRUE
            OR m.time_gap_seconds IS NULL
            OR m.time_gap_seconds > %s
        )
        ORDER BY v.timestamp_readable, v.symbol;
    """

    cursor.execute(query, (lookback_hours, valid_window_seconds))

    return normalize_quote_dataframe(
        rows_to_dataframe(
            cursor,
            ["symbol", "vnx_price", "timestamp_readable"],
        ),
        time_columns=["timestamp_readable"],
        number_columns=["vnx_price"],
    )


def load_unmatched_vnx_rows(cursor, lookback_hours):
    return load_vnx_rows_to_match(cursor, lookback_hours)


def load_delayed_rows_for_vnx_window(cursor, vnx_df, padding_seconds):
    if vnx_df.empty:
        return pd.DataFrame(
            columns=["symbol", "delayed_price", "delayed_time_readable"],
        )

    window_start = vnx_df["timestamp_readable"].min() - timedelta(
        seconds=padding_seconds,
    )
    window_end = vnx_df["timestamp_readable"].max() + timedelta(
        seconds=padding_seconds,
    )

    query = """
        SELECT
            symbol,
            delayed_price,
            delayed_time_readable
        FROM delayed_quotes
        WHERE delayed_time_readable >= %s
          AND delayed_time_readable <= %s
        ORDER BY delayed_time_readable, symbol;
    """

    cursor.execute(query, (window_start, window_end))

    return normalize_quote_dataframe(
        rows_to_dataframe(
            cursor,
            ["symbol", "delayed_price", "delayed_time_readable"],
        ),
        time_columns=["delayed_time_readable"],
        number_columns=["delayed_price"],
    )


def match_unmatched_postgres_quotes_to_delayed(
    valid_window_seconds=60,
    lookback_hours=24,
    delayed_padding_seconds=900,
):
    """
    Match raw PostgreSQL VNX rows to raw delayed rows.

    Recent unmatched rows and previous invalid/wide matches are both included.
    This lets the matcher repair rows that were matched before the 15-minute
    delayed/reference feed caught up.

    This is the production matcher path for cloud/local PostgreSQL pipelines.
    It does not depend on CSV backups.
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            vnx_df = load_vnx_rows_to_match(
                cursor,
                lookback_hours,
                valid_window_seconds,
            )
            delayed_df = load_delayed_rows_for_vnx_window(
                cursor,
                vnx_df,
                delayed_padding_seconds,
            )

    if vnx_df.empty or delayed_df.empty:
        return pd.DataFrame()

    matched_df = match_vnx_rows_to_delayed(
        vnx_df=vnx_df,
        delayed_df=delayed_df,
        valid_window_seconds=valid_window_seconds,
    )

    return normalize_matched_dataframe(matched_df)
