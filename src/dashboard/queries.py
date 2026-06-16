import pandas as pd
from sqlalchemy import create_engine

from src.settings import get_sqlalchemy_database_url


def get_database_engine():
    """
    Create a SQLAlchemy engine for PostgreSQL.
    """

    return create_engine(get_sqlalchemy_database_url())


def get_available_date_range():
    """
    Get the earliest and latest available VNX dates from matched_quote_analysis.
    """

    engine = get_database_engine()

    query = """
        SELECT
            MIN(DATE(vnx_time)) AS min_date,
            MAX(DATE(vnx_time)) AS max_date
        FROM matched_quote_analysis;
    """

    df = pd.read_sql_query(query, engine)

    if df.empty or pd.isna(df.loc[0, "min_date"]) or pd.isna(df.loc[0, "max_date"]):
        return None, None

    return df.loc[0, "min_date"], df.loc[0, "max_date"]


def get_symbols():
    """
    Load symbols and company metadata from sp500_symbols.
    """

    engine = get_database_engine()

    query = """
        SELECT
            symbol,
            company_name,
            sector,
            sub_industry
        FROM sp500_symbols
        ORDER BY symbol;
    """

    return pd.read_sql_query(query, engine)


def get_sectors():
    """
    Load available sectors from sp500_symbols.
    """

    engine = get_database_engine()

    query = """
        SELECT DISTINCT sector
        FROM sp500_symbols
        WHERE sector IS NOT NULL
        ORDER BY sector;
    """

    df = pd.read_sql_query(query, engine)

    return df["sector"].dropna().tolist()


def load_matched_data(
    start_date,
    end_date,
    selected_symbols=None,
    selected_sectors=None,
    max_time_gap_seconds=60,
    valid_only=True,
):
    """
    Load matched quote data from PostgreSQL using dashboard filters.

    Date filtering is based on vnx_time because VNX drives the comparison.
    """

    engine = get_database_engine()

    conditions = [
        "DATE(m.vnx_time) >= %(start_date)s",
        "DATE(m.vnx_time) <= %(end_date)s",
    ]

    params = {
        "start_date": start_date,
        "end_date": end_date,
    }

    if valid_only:
        conditions.append("m.valid_match = TRUE")

    if max_time_gap_seconds is not None:
        conditions.append("m.time_gap_seconds <= %(max_time_gap_seconds)s")
        params["max_time_gap_seconds"] = max_time_gap_seconds

    if selected_symbols:
        conditions.append("m.symbol = ANY(%(selected_symbols)s)")
        params["selected_symbols"] = selected_symbols

    if selected_sectors:
        conditions.append("s.sector = ANY(%(selected_sectors)s)")
        params["selected_sectors"] = selected_sectors

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            m.symbol,
            s.company_name,
            s.sector,
            s.sub_industry,
            m.vnx_price,
            m.vnx_time,
            m.delayed_price,
            m.delayed_time,
            m.time_gap_seconds,
            m.valid_match,
            m.difference,
            m.percentage_error,
            m.absolute_percentage_error
        FROM matched_quote_analysis m
        INNER JOIN sp500_symbols s
            ON m.symbol = s.symbol
        WHERE {where_clause}
        ORDER BY m.vnx_time, m.symbol;
    """

    df = pd.read_sql_query(query, engine, params=params)

    if not df.empty:
        df["vnx_time"] = pd.to_datetime(df["vnx_time"], errors="coerce")
        df["delayed_time"] = pd.to_datetime(df["delayed_time"], errors="coerce")

    return df


def load_raw_data_coverage():
    """
    Load raw data coverage summary from PostgreSQL.
    """

    engine = get_database_engine()

    query = """
        SELECT
            s.symbol,
            s.company_name,
            s.sector,
            s.sub_industry,
            COALESCE(v.vnx_raw_rows, 0) AS vnx_raw_rows,
            COALESCE(d.delayed_raw_rows, 0) AS delayed_raw_rows,
            COALESCE(m.matched_rows, 0) AS matched_rows,
            v.earliest_vnx_time,
            v.latest_vnx_time,
            d.earliest_delayed_time,
            d.latest_delayed_time
        FROM sp500_symbols s
        LEFT JOIN (
            SELECT
                symbol,
                COUNT(*) AS vnx_raw_rows,
                MIN(timestamp_readable) AS earliest_vnx_time,
                MAX(timestamp_readable) AS latest_vnx_time
            FROM vnx_quotes
            GROUP BY symbol
        ) v
            ON s.symbol = v.symbol
        LEFT JOIN (
            SELECT
                symbol,
                COUNT(*) AS delayed_raw_rows,
                MIN(delayed_time_readable) AS earliest_delayed_time,
                MAX(delayed_time_readable) AS latest_delayed_time
            FROM delayed_quotes
            GROUP BY symbol
        ) d
            ON s.symbol = d.symbol
        LEFT JOIN (
            SELECT
                symbol,
                COUNT(*) AS matched_rows
            FROM matched_quote_analysis
            GROUP BY symbol
        ) m
            ON s.symbol = m.symbol
        ORDER BY s.symbol;
    """

    return pd.read_sql_query(query, engine)


def load_timestamp_window_summary(
    start_date,
    end_date,
    selected_symbols=None,
    selected_sectors=None,
):
    """
    Calculate timestamp-window analysis from PostgreSQL data.

    This tests how many observations are valid under each timestamp window
    and what the accuracy looks like under that window.
    """

    windows = [1, 5, 15, 30, 60]
    rows = []

    for window in windows:
        df = load_matched_data(
            start_date=start_date,
            end_date=end_date,
            selected_symbols=selected_symbols,
            selected_sectors=selected_sectors,
            max_time_gap_seconds=window,
            valid_only=True,
        )

        if df.empty:
            rows.append(
                {
                    "timestamp_window_seconds": window,
                    "observations": 0,
                    "symbols_analyzed": 0,
                    "avg_price_error_pct": None,
                    "median_price_error_pct": None,
                    "max_price_error_pct": None,
                    "avg_directional_error_pct": None,
                    "avg_time_gap_seconds": None,
                }
            )
            continue

        rows.append(
            {
                "timestamp_window_seconds": window,
                "observations": len(df),
                "symbols_analyzed": df["symbol"].nunique(),
                "avg_price_error_pct": df["absolute_percentage_error"].mean(),
                "median_price_error_pct": df["absolute_percentage_error"].median(),
                "max_price_error_pct": df["absolute_percentage_error"].max(),
                "avg_directional_error_pct": df["percentage_error"].mean(),
                "avg_time_gap_seconds": df["time_gap_seconds"].mean(),
            }
        )

    return pd.DataFrame(rows)
