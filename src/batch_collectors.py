import os
import pandas as pd
from datetime import datetime

from src.batch_client import get_vnx_quotes_batch, get_delayed_quotes_batch


def save_rows_to_csv(rows, file_path, duplicate_columns):
    """
    Save rows to CSV while removing duplicates.

    This function:
    1. Reads existing CSV if it exists.
    2. Cleans duplicates already present in existing data.
    3. Adds only truly new rows.
    4. Prevents negative saved row counts.
    """

    if not rows:
        return {
            "saved_rows": 0,
            "skipped_rows": 0,
            "cleaned_existing_duplicates": 0,
            "reason": "No rows to save"
        }

    new_df = pd.DataFrame(rows)

    new_df = new_df.drop_duplicates(
        subset=duplicate_columns,
        keep="first"
    )

    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        existing_df = pd.read_csv(file_path, low_memory=False)

        existing_count_before_cleaning = len(existing_df)

        existing_df = existing_df.drop_duplicates(
            subset=duplicate_columns,
            keep="first"
        )

        existing_count_after_cleaning = len(existing_df)

        cleaned_existing_duplicates = (
            existing_count_before_cleaning - existing_count_after_cleaning
        )

        combined_df = pd.concat(
            [existing_df, new_df],
            ignore_index=True
        )

        combined_df = combined_df.drop_duplicates(
            subset=duplicate_columns,
            keep="first"
        )

        saved_rows = len(combined_df) - len(existing_df)
        skipped_rows = len(new_df) - saved_rows

    else:
        combined_df = new_df
        saved_rows = len(new_df)
        skipped_rows = 0
        cleaned_existing_duplicates = 0

    combined_df.to_csv(file_path, index=False)

    return {
        "saved_rows": saved_rows,
        "skipped_rows": skipped_rows,
        "cleaned_existing_duplicates": cleaned_existing_duplicates,
        "reason": "Rows saved with duplicate check"
    }


def collect_vnx_quotes_batch(symbols):
    """
    Collect VNX quotes for multiple symbols.

    Saves to CSV backup and returns collected rows for PostgreSQL insertion.
    """

    quotes = get_vnx_quotes_batch(symbols)

    rows = []

    collection_timestamp = datetime.now()

    for quote in quotes:
        rows.append({
            "symbol": quote["symbol"],
            "vnx_price": quote["vnx_price"],
            "bid_price": quote["bid_price"],
            "ask_price": quote["ask_price"],
            "last_sale_price": quote["last_sale_price"],
            "timestamp_raw": quote["timestamp_raw"],
            "timestamp_readable": quote["timestamp_readable"],
            "collection_time": collection_timestamp,
            "collected_at": collection_timestamp,
            "price_type": quote["price_type"]
        })

    file_path = "data/raw/vnx_quote_history.csv"

    csv_status = save_rows_to_csv(
        rows=rows,
        file_path=file_path,
        duplicate_columns=["symbol", "timestamp_raw"]
    )

    csv_status["rows"] = rows
    csv_status["collected_rows"] = len(rows)

    return csv_status


def collect_delayed_quotes_batch(symbols):
    """
    Collect delayed quotes for multiple symbols.

    Saves to CSV backup and returns collected rows for PostgreSQL insertion.
    """

    quotes = get_delayed_quotes_batch(symbols)

    rows = []

    collection_timestamp = datetime.now()

    for quote in quotes:
        rows.append({
            "symbol": quote["symbol"],
            "delayed_price": quote["delayed_price"],
            "high": quote["high"],
            "low": quote["low"],
            "delayed_size": quote["delayed_size"],
            "delayed_time_raw": quote["delayed_time_raw"],
            "delayed_time_readable": quote["delayed_time_readable"],
            "total_volume": quote["total_volume"],
            "processed_time_raw": quote["processed_time_raw"],
            "processed_time_readable": quote["processed_time_readable"],
            "collection_time": collection_timestamp,
            "collected_at": collection_timestamp
        })

    file_path = "data/raw/delayed_quote_history.csv"

    csv_status = save_rows_to_csv(
        rows=rows,
        file_path=file_path,
        duplicate_columns=["symbol", "delayed_time_raw"]
    )

    csv_status["rows"] = rows
    csv_status["collected_rows"] = len(rows)

    return csv_status