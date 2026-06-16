from pathlib import Path

import pandas as pd
from psycopg2.extras import execute_values

from src.database.connection import get_connection


SP500_SYMBOLS_FILE = Path("config/sp500_symbols.csv")
VNX_RAW_FILE = Path("data/raw/vnx_quote_history.csv")
DELAYED_RAW_FILE = Path("data/raw/delayed_quote_history.csv")
MATCHED_ANALYSIS_FILE = Path("data/processed/matched_quote_analysis.csv")


def load_csv(file_path):
    """
    Safely load a CSV file.
    """

    if not file_path.exists() or file_path.stat().st_size == 0:
        print(f"Skipping missing or empty file: {file_path}")
        return pd.DataFrame()

    return pd.read_csv(file_path)


def parse_datetime_column(df, column_name):
    """
    Safely parse datetime columns.
    """

    if df.empty or column_name not in df.columns:
        return df

    df[column_name] = pd.to_datetime(
        df[column_name],
        format="mixed",
        errors="coerce"
    )

    return df


def clean_numeric_column(df, column_name):
    """
    Convert a column to numeric safely.
    """

    if df.empty or column_name not in df.columns:
        return df

    df[column_name] = pd.to_numeric(df[column_name], errors="coerce")

    return df


def clean_boolean_column(df, column_name):
    """
    Convert common boolean strings without turning "False" into True.
    """

    if df.empty or column_name not in df.columns:
        return df

    mapping = {
        "true": True,
        "1": True,
        "yes": True,
        "y": True,
        "false": False,
        "0": False,
        "no": False,
        "n": False,
    }

    df[column_name] = (
        df[column_name]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(mapping)
    )

    return df


def import_sp500_symbols():
    """
    Import S&P 500 symbol universe into PostgreSQL.
    """

    df = load_csv(SP500_SYMBOLS_FILE)

    if df.empty:
        return 0

    required_columns = ["symbol", "company_name", "sector", "sub_industry"]

    for column in required_columns:
        if column not in df.columns:
            df[column] = None

    df = df[required_columns].copy()

    df["symbol"] = df["symbol"].astype(str).str.strip()
    df = df.dropna(subset=["symbol"])
    df = df[df["symbol"] != ""]

    rows = list(df.itertuples(index=False, name=None))

    query = """
        INSERT INTO sp500_symbols (
            symbol,
            company_name,
            sector,
            sub_industry
        )
        VALUES %s
        ON CONFLICT (symbol)
        DO UPDATE SET
            company_name = EXCLUDED.company_name,
            sector = EXCLUDED.sector,
            sub_industry = EXCLUDED.sub_industry;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            execute_values(cursor, query, rows)
        connection.commit()

    print(f"Imported S&P 500 symbols: {len(rows)}")
    return len(rows)


def import_vnx_quotes():
    """
    Import raw VNX quote history into PostgreSQL.
    """

    df = load_csv(VNX_RAW_FILE)

    if df.empty:
        return 0

    required_columns = ["symbol", "vnx_price", "timestamp_readable"]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(f"Missing required VNX column: {column}")

    if "collected_at" not in df.columns:
        df["collected_at"] = None

    df = df[
        [
            "symbol",
            "vnx_price",
            "timestamp_readable",
            "collected_at"
        ]
    ].copy()

    df["symbol"] = df["symbol"].astype(str).str.strip()

    df = clean_numeric_column(df, "vnx_price")
    df = parse_datetime_column(df, "timestamp_readable")
    df = parse_datetime_column(df, "collected_at")

    df = df.dropna(subset=["symbol", "timestamp_readable"])
    df = df[df["symbol"] != ""]

    rows = [
        (
            row.symbol,
            row.vnx_price,
            row.timestamp_readable.to_pydatetime()
            if pd.notna(row.timestamp_readable)
            else None,
            row.collected_at.to_pydatetime()
            if pd.notna(row.collected_at)
            else None,
        )
        for row in df.itertuples(index=False)
    ]

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
            execute_values(cursor, query, rows)
        connection.commit()

    print(f"Imported VNX raw quote rows: {len(rows)}")
    return len(rows)


def import_delayed_quotes():
    """
    Import raw delayed quote history into PostgreSQL.
    """

    df = load_csv(DELAYED_RAW_FILE)

    if df.empty:
        return 0

    required_columns = ["symbol", "delayed_price", "delayed_time_readable"]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(f"Missing required delayed quote column: {column}")

    if "collected_at" not in df.columns:
        df["collected_at"] = None

    df = df[
        [
            "symbol",
            "delayed_price",
            "delayed_time_readable",
            "collected_at"
        ]
    ].copy()

    df["symbol"] = df["symbol"].astype(str).str.strip()

    df = clean_numeric_column(df, "delayed_price")
    df = parse_datetime_column(df, "delayed_time_readable")
    df = parse_datetime_column(df, "collected_at")

    df = df.dropna(subset=["symbol", "delayed_time_readable"])
    df = df[df["symbol"] != ""]

    rows = [
        (
            row.symbol,
            row.delayed_price,
            row.delayed_time_readable.to_pydatetime()
            if pd.notna(row.delayed_time_readable)
            else None,
            row.collected_at.to_pydatetime()
            if pd.notna(row.collected_at)
            else None,
        )
        for row in df.itertuples(index=False)
    ]

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
            execute_values(cursor, query, rows)
        connection.commit()

    print(f"Imported delayed raw quote rows: {len(rows)}")
    return len(rows)


def import_matched_quote_analysis():
    """
    Import matched quote analysis into PostgreSQL.
    """

    df = load_csv(MATCHED_ANALYSIS_FILE)

    if df.empty:
        return 0

    required_columns = [
        "symbol",
        "vnx_price",
        "vnx_time",
        "delayed_price",
        "delayed_time",
        "time_gap_seconds",
        "valid_match",
        "difference",
        "percentage_error",
        "absolute_percentage_error",
    ]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(f"Missing required matched analysis column: {column}")

    df = df[required_columns].copy()

    df["symbol"] = df["symbol"].astype(str).str.strip()

    numeric_columns = [
        "vnx_price",
        "delayed_price",
        "time_gap_seconds",
        "difference",
        "percentage_error",
        "absolute_percentage_error",
    ]

    for column in numeric_columns:
        df = clean_numeric_column(df, column)

    df = parse_datetime_column(df, "vnx_time")
    df = parse_datetime_column(df, "delayed_time")

    df = clean_boolean_column(df, "valid_match")

    df = df.dropna(subset=["symbol", "vnx_time"])
    df = df[df["symbol"] != ""]

    rows = [
        (
            row.symbol,
            row.vnx_price,
            row.vnx_time.to_pydatetime()
            if pd.notna(row.vnx_time)
            else None,
            row.delayed_price,
            row.delayed_time.to_pydatetime()
            if pd.notna(row.delayed_time)
            else None,
            row.time_gap_seconds,
            row.valid_match,
            row.difference,
            row.percentage_error,
            row.absolute_percentage_error,
        )
        for row in df.itertuples(index=False)
    ]

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
            execute_values(cursor, query, rows)
        connection.commit()

    print(f"Imported matched quote analysis rows: {len(rows)}")
    return len(rows)


def import_all_csv_files():
    """
    Import all current CSV files into PostgreSQL.
    """

    print()
    print("Importing CSV data into PostgreSQL")
    print("==================================")

    imported_counts = {
        "sp500_symbols": import_sp500_symbols(),
        "vnx_quotes": import_vnx_quotes(),
        "delayed_quotes": import_delayed_quotes(),
        "matched_quote_analysis": import_matched_quote_analysis(),
    }

    print()
    print("Import Summary")
    print("--------------")

    for table_name, count in imported_counts.items():
        print(f"{table_name}: {count} rows processed")

    return imported_counts
