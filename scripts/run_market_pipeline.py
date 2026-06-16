import time
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

from config.symbols import ACTIVE_SYMBOLS
from src.settings import get_bool_env, get_int_env
from src.batch_collectors import (
    collect_vnx_quotes_batch,
    collect_delayed_quotes_batch
)
from src.matcher import (
    match_all_vnx_quotes_to_delayed,
    normalize_matched_dataframe,
    save_matched_results,
)
from src.database.writer import (
    insert_vnx_quote_rows,
    insert_delayed_quote_rows,
    insert_matched_quote_rows,
)


# -----------------------------
# Settings
# -----------------------------

SYMBOLS = ACTIVE_SYMBOLS

BATCH_SIZE = get_int_env("BATCH_SIZE", 100, min_value=1)

COLLECTION_INTERVAL_SECONDS = get_int_env(
    "COLLECTION_INTERVAL_SECONDS",
    60,
    min_value=1,
)

MATCHER_INTERVAL_SECONDS = get_int_env(
    "MATCHER_INTERVAL_SECONDS",
    300,
    min_value=1,
)

MATCHER_VALID_WINDOW_SECONDS = get_int_env(
    "MATCHER_VALID_WINDOW_SECONDS",
    60,
    min_value=1,
)

EASTERN_TIMEZONE = ZoneInfo("America/New_York")

MARKET_OPEN = dt_time(9, 30)
MARKET_CLOSE = dt_time(16, 0)

SAVE_CSV_BACKUP = get_bool_env("SAVE_CSV_BACKUP", True)


# -----------------------------
# Market hours check
# -----------------------------

def is_market_open_now():
    """
    Check if current Eastern Time is within regular US market hours.
    """

    current_time = datetime.now(EASTERN_TIMEZONE)

    is_weekday = current_time.weekday() < 5
    is_market_hours = MARKET_OPEN <= current_time.time() <= MARKET_CLOSE

    return is_weekday and is_market_hours, current_time


# -----------------------------
# Batching helper
# -----------------------------

def split_into_batches(items, batch_size):
    """
    Split a list into smaller batches.
    """

    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


# -----------------------------
# Batch collection
# -----------------------------

def summarize_status(status):
    """
    Return status dictionary without raw rows for clean terminal output.
    """

    return {
        key: value
        for key, value in status.items()
        if key != "rows"
    }

def collect_all_symbols_in_batches():
    """
    Collect VNX and delayed quotes for all active symbols using batch API calls.

    Data is saved to CSV backup by batch_collectors and inserted into PostgreSQL
    by database writer functions.
    """

    total_collected_vnx = 0
    total_collected_delayed = 0

    total_csv_saved_vnx = 0
    total_csv_saved_delayed = 0
    total_csv_skipped_vnx = 0
    total_csv_skipped_delayed = 0

    total_db_inserted_vnx = 0
    total_db_inserted_delayed = 0

    total_cleaned_vnx_duplicates = 0
    total_cleaned_delayed_duplicates = 0

    total_errors = 0

    for batch_number, symbol_batch in enumerate(
        split_into_batches(SYMBOLS, BATCH_SIZE),
        start=1
    ):
        print()
        print(f"Collecting batch {batch_number}: {len(symbol_batch)} symbols")
        print("Symbols:", ", ".join(symbol_batch))

        try:
            vnx_status = collect_vnx_quotes_batch(
                symbol_batch,
                save_csv_backup=SAVE_CSV_BACKUP,
            )
            delayed_status = collect_delayed_quotes_batch(
                symbol_batch,
                save_csv_backup=SAVE_CSV_BACKUP,
            )

            vnx_rows = vnx_status.get("rows", [])
            delayed_rows = delayed_status.get("rows", [])

            inserted_vnx_count = insert_vnx_quote_rows(vnx_rows)
            inserted_delayed_count = insert_delayed_quote_rows(delayed_rows)

            total_collected_vnx += len(vnx_rows)
            total_collected_delayed += len(delayed_rows)

            total_csv_saved_vnx += vnx_status["saved_rows"]
            total_csv_saved_delayed += delayed_status["saved_rows"]

            total_csv_skipped_vnx += vnx_status["skipped_rows"]
            total_csv_skipped_delayed += delayed_status["skipped_rows"]

            total_db_inserted_vnx += inserted_vnx_count
            total_db_inserted_delayed += inserted_delayed_count

            total_cleaned_vnx_duplicates += vnx_status.get(
                "cleaned_existing_duplicates",
                0
            )

            total_cleaned_delayed_duplicates += delayed_status.get(
                "cleaned_existing_duplicates",
                0
            )

            print("VNX CSV:", summarize_status(vnx_status))
            print("Delayed CSV:", summarize_status(delayed_status))
            print("VNX PostgreSQL rows processed:", inserted_vnx_count)
            print("Delayed PostgreSQL rows processed:", inserted_delayed_count)

        except Exception as error:
            total_errors += 1
            print("Batch collection error:", error)

    return {
        "collected_vnx_count": total_collected_vnx,
        "collected_delayed_count": total_collected_delayed,

        "csv_saved_vnx_count": total_csv_saved_vnx,
        "csv_saved_delayed_count": total_csv_saved_delayed,
        "csv_skipped_vnx_count": total_csv_skipped_vnx,
        "csv_skipped_delayed_count": total_csv_skipped_delayed,

        "db_inserted_vnx_count": total_db_inserted_vnx,
        "db_inserted_delayed_count": total_db_inserted_delayed,

        "cleaned_vnx_duplicates": total_cleaned_vnx_duplicates,
        "cleaned_delayed_duplicates": total_cleaned_delayed_duplicates,

        "error_count": total_errors
    }


# -----------------------------
# Matcher
# -----------------------------

def run_matcher():
    """
    Run VNX-driven matcher and save processed matched results.

    Matched results are saved to CSV backup and inserted into PostgreSQL.
    """

    matched_df = match_all_vnx_quotes_to_delayed(
        valid_window_seconds=MATCHER_VALID_WINDOW_SECONDS,
        incremental=True
    )

    print(f"Matched rows before cleanup: {len(matched_df)}")

    matched_df = normalize_matched_dataframe(matched_df)

    print(f"Matched rows after cleanup: {len(matched_df)}")

    save_status = save_matched_results(matched_df)
    db_inserted_matches = insert_matched_quote_rows(matched_df)

    total_matches = len(matched_df)

    if matched_df.empty:
        valid_matches = 0
        invalid_matches = 0
        symbol_count = 0
    else:
        valid_matches = len(matched_df[matched_df["valid_match"] == True])
        invalid_matches = total_matches - valid_matches
        symbol_count = matched_df["symbol"].nunique()

    print()
    print("Matcher Summary")
    print("---------------")
    print("Total matched rows generated:", total_matches)
    print("Valid matches:", valid_matches)
    print("Invalid matches:", invalid_matches)
    print("Symbols matched:", symbol_count)
    print("CSV new rows saved:", save_status["saved_rows"])
    print("PostgreSQL matched rows processed:", db_inserted_matches)
    print("Save status:", save_status["reason"])


# -----------------------------
# Main pipeline loop
# -----------------------------

def main():
    """
    Run the automated market-hours collection pipeline.
    """

    last_matcher_run_time = 0

    while True:
        market_is_open, current_time = is_market_open_now()

        print()
        print("==================================================")
        print("Current Eastern Time:", current_time)
        print("Active Symbols:", len(SYMBOLS))
        print("Batch Size:", BATCH_SIZE)
        print("CSV Backup Enabled:", SAVE_CSV_BACKUP)

        if market_is_open:
            print("Market is open. Running batch collection...")

            collection_summary = collect_all_symbols_in_batches()

            print()
            print("Collection Summary")
            print("------------------")
            print("Collected VNX rows:", collection_summary["collected_vnx_count"])
            print("Collected delayed rows:", collection_summary["collected_delayed_count"])
            print("CSV saved VNX quotes:", collection_summary["csv_saved_vnx_count"])
            print("CSV saved delayed quotes:", collection_summary["csv_saved_delayed_count"])
            print("CSV skipped VNX duplicates:", collection_summary["csv_skipped_vnx_count"])
            print("CSV skipped delayed duplicates:", collection_summary["csv_skipped_delayed_count"])
            print("PostgreSQL VNX rows processed:", collection_summary["db_inserted_vnx_count"])
            print("PostgreSQL delayed rows processed:", collection_summary["db_inserted_delayed_count"])
            print("Cleaned existing VNX duplicates:", collection_summary["cleaned_vnx_duplicates"])
            print("Cleaned existing delayed duplicates:", collection_summary["cleaned_delayed_duplicates"])
            print("Batch collection errors:", collection_summary["error_count"])

            current_timestamp = time.time()

            should_run_matcher = (
                current_timestamp - last_matcher_run_time
            ) >= MATCHER_INTERVAL_SECONDS

            if should_run_matcher:
                print()
                print("Running matcher...")
                run_matcher()
                last_matcher_run_time = current_timestamp

            else:
                seconds_until_next_matcher = int(
                    MATCHER_INTERVAL_SECONDS - (
                        current_timestamp - last_matcher_run_time
                    )
                )

                print()
                print("Skipping matcher this cycle.")
                print("Next matcher run in about", seconds_until_next_matcher, "seconds.")

        else:
            print("Market is closed. Waiting...")

        print()
        print("Waiting", COLLECTION_INTERVAL_SECONDS, "seconds...")
        time.sleep(COLLECTION_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
