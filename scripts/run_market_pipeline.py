import os
import time
from datetime import datetime

from config.symbols import ACTIVE_SYMBOLS
from src.settings import get_bool_env, get_int_env
from src.collection_audit import (
    build_snapshot_audit_rows,
    summarize_snapshot_audit_rows,
)
from src.batch_collectors import (
    collect_vnx_quotes_batch,
    collect_delayed_quotes_batch
)
from src.matcher import (
    normalize_matched_dataframe,
    save_matched_results,
)
from src.database.writer import (
    insert_vnx_quote_rows,
    insert_delayed_quote_rows,
    insert_matched_quote_rows,
    insert_quote_snapshot_audit_rows,
)
from src.database.pipeline_health import record_pipeline_event
from src.database.postgres_matcher import match_unmatched_postgres_quotes_to_delayed
from src.database.retention import prune_quote_history
from src.market_hours import is_market_open_now


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

SAVE_CSV_BACKUP = get_bool_env("SAVE_CSV_BACKUP", True)

HEALTH_HEARTBEAT_INTERVAL_SECONDS = get_int_env(
    "HEALTH_HEARTBEAT_INTERVAL_SECONDS",
    300,
    min_value=1,
)

MATCHER_LOOKBACK_HOURS = get_int_env(
    "MATCHER_LOOKBACK_HOURS",
    24,
    min_value=1,
)

MATCHER_DELAYED_PADDING_SECONDS = get_int_env(
    "MATCHER_DELAYED_PADDING_SECONDS",
    900,
    min_value=1,
)

RAW_RETENTION_DAYS = get_int_env(
    "RAW_RETENTION_DAYS",
    1,
    min_value=0,
)

MATCHED_RETENTION_DAYS = get_int_env(
    "MATCHED_RETENTION_DAYS",
    0,
    min_value=0,
)

RETENTION_INTERVAL_SECONDS = get_int_env(
    "RETENTION_INTERVAL_SECONDS",
    3600,
    min_value=60,
)

MATCHED_REPLICA_DATABASE_URL = os.getenv("MATCHED_REPLICA_DATABASE_URL")


def write_pipeline_event(component, status, message=None, details=None):
    """
    Record health events without letting observability stop collection.
    """

    try:
        record_pipeline_event(
            component=component,
            status=status,
            message=message,
            details=details,
        )
    except Exception as error:
        print("Pipeline health event failed:", error)


def write_replica_pipeline_event(component, status, message=None, details=None):
    """
    Mirror lightweight health events to the cloud dashboard database.
    """

    if not MATCHED_REPLICA_DATABASE_URL:
        return

    try:
        record_pipeline_event(
            component=component,
            status=status,
            message=message,
            details=details,
            database_url=MATCHED_REPLICA_DATABASE_URL,
        )
    except Exception as error:
        print("Replica pipeline health event failed:", error)


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

    Data is saved to CSV backup by batch_collectors, inserted into PostgreSQL
    by database writer functions, and audited per requested symbol so we can
    prove whether every polling cycle returned every symbol.
    """

    cycle_timestamp = datetime.now()

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
    audit_rows = []

    for batch_number, symbol_batch in enumerate(
        split_into_batches(SYMBOLS, BATCH_SIZE),
        start=1
    ):
        print()
        print(f"Collecting batch {batch_number}: {len(symbol_batch)} symbols")
        print("Symbols:", ", ".join(symbol_batch))

        vnx_rows = []
        vnx_error = None

        try:
            vnx_status = collect_vnx_quotes_batch(
                symbol_batch,
                save_csv_backup=SAVE_CSV_BACKUP,
                collection_timestamp=cycle_timestamp,
            )
            vnx_rows = vnx_status.get("rows", [])
            inserted_vnx_count = insert_vnx_quote_rows(vnx_rows)

            total_collected_vnx += len(vnx_rows)
            total_csv_saved_vnx += vnx_status["saved_rows"]
            total_csv_skipped_vnx += vnx_status["skipped_rows"]
            total_db_inserted_vnx += inserted_vnx_count
            total_cleaned_vnx_duplicates += vnx_status.get(
                "cleaned_existing_duplicates",
                0
            )

            print("VNX CSV:", summarize_status(vnx_status))
            print("VNX PostgreSQL rows processed:", inserted_vnx_count)

        except Exception as error:
            total_errors += 1
            vnx_error = str(error)
            print("VNX batch collection error:", error)

        audit_rows.extend(
            build_snapshot_audit_rows(
                source="vnx",
                requested_symbols=symbol_batch,
                returned_rows=vnx_rows,
                cycle_id=cycle_timestamp,
                batch_number=batch_number,
                timestamp_field="timestamp_readable",
                price_field="vnx_price",
                error_message=vnx_error,
            )
        )

        delayed_rows = []
        delayed_error = None

        try:
            delayed_status = collect_delayed_quotes_batch(
                symbol_batch,
                save_csv_backup=SAVE_CSV_BACKUP,
                collection_timestamp=cycle_timestamp,
            )

            delayed_rows = delayed_status.get("rows", [])
            inserted_delayed_count = insert_delayed_quote_rows(delayed_rows)

            total_collected_delayed += len(delayed_rows)
            total_csv_saved_delayed += delayed_status["saved_rows"]
            total_csv_skipped_delayed += delayed_status["skipped_rows"]
            total_db_inserted_delayed += inserted_delayed_count
            total_cleaned_delayed_duplicates += delayed_status.get(
                "cleaned_existing_duplicates",
                0
            )

            print("Delayed CSV:", summarize_status(delayed_status))
            print("Delayed PostgreSQL rows processed:", inserted_delayed_count)

        except Exception as error:
            total_errors += 1
            delayed_error = str(error)
            print("Delayed batch collection error:", error)

        audit_rows.extend(
            build_snapshot_audit_rows(
                source="delayed",
                requested_symbols=symbol_batch,
                returned_rows=delayed_rows,
                cycle_id=cycle_timestamp,
                batch_number=batch_number,
                timestamp_field="delayed_time_readable",
                price_field="delayed_price",
                error_message=delayed_error,
            )
        )

    audit_inserted_count = 0
    audit_error = None

    try:
        audit_inserted_count = insert_quote_snapshot_audit_rows(audit_rows)
    except Exception as error:
        audit_error = str(error)
        print("Snapshot audit insert error:", audit_error)

    snapshot_coverage = summarize_snapshot_audit_rows(audit_rows)

    return {
        "cycle_started_at": cycle_timestamp,
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

        "snapshot_audit_rows_processed": len(audit_rows),
        "snapshot_audit_rows_inserted": audit_inserted_count,
        "snapshot_audit_error": audit_error,
        "snapshot_coverage": snapshot_coverage,

        "error_count": total_errors
    }


# -----------------------------
# Matcher
# -----------------------------

def run_matcher():
    """
    Run PostgreSQL-backed VNX-driven matcher.
    """

    matched_df = match_unmatched_postgres_quotes_to_delayed(
        valid_window_seconds=MATCHER_VALID_WINDOW_SECONDS,
        lookback_hours=MATCHER_LOOKBACK_HOURS,
        delayed_padding_seconds=MATCHER_DELAYED_PADDING_SECONDS,
    )

    print(f"Matched rows before cleanup: {len(matched_df)}")

    matched_df = normalize_matched_dataframe(matched_df)

    print(f"Matched rows after cleanup: {len(matched_df)}")

    if SAVE_CSV_BACKUP:
        save_status = save_matched_results(matched_df)
    else:
        save_status = {
            "saved_rows": 0,
            "reason": "CSV backup disabled",
        }

    db_inserted_matches = insert_matched_quote_rows(matched_df)
    replica_inserted_matches = 0
    replica_error = None

    if MATCHED_REPLICA_DATABASE_URL and not matched_df.empty:
        try:
            replica_inserted_matches = insert_matched_quote_rows(
                matched_df,
                database_url=MATCHED_REPLICA_DATABASE_URL,
            )
            record_pipeline_event(
                "laptop_matched_replica",
                "success",
                "Matched rows synced from laptop worker.",
                {
                    "matched_rows_synced": replica_inserted_matches,
                    "local_matched_rows_processed": db_inserted_matches,
                },
                database_url=MATCHED_REPLICA_DATABASE_URL,
            )
        except Exception as error:
            replica_error = str(error)
            print("Matched replica sync error:", replica_error)

            try:
                record_pipeline_event(
                    "laptop_matched_replica",
                    "error",
                    replica_error,
                    {
                        "local_matched_rows_processed": db_inserted_matches,
                    },
                    database_url=MATCHED_REPLICA_DATABASE_URL,
                )
            except Exception as health_error:
                print("Replica health event failed:", health_error)

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
    print("Replica matched rows processed:", replica_inserted_matches)
    print("Save status:", save_status["reason"])

    return {
        "total_matches": total_matches,
        "valid_matches": valid_matches,
        "invalid_matches": invalid_matches,
        "symbol_count": symbol_count,
        "csv_saved_rows": save_status["saved_rows"],
        "db_inserted_matches": db_inserted_matches,
        "replica_inserted_matches": replica_inserted_matches,
        "replica_error": replica_error,
        "save_reason": save_status["reason"],
    }


def run_retention_cleanup():
    """
    Prune old quote history so live raw collection does not fill the database.
    """

    summary = prune_quote_history(
        raw_retention_days=RAW_RETENTION_DAYS,
        matched_retention_days=MATCHED_RETENTION_DAYS,
    )

    print()
    print("Retention Cleanup Summary")
    print("-------------------------")
    print("Raw retention days:", summary["raw_retention_days"])
    print("Matched retention days:", summary["matched_retention_days"])
    print("VNX raw rows deleted:", summary["vnx_rows_deleted"])
    print("Delayed raw rows deleted:", summary["delayed_rows_deleted"])
    print("Matched rows deleted:", summary["matched_rows_deleted"])

    return summary


# -----------------------------
# Main pipeline loop
# -----------------------------

def main():
    """
    Run the automated market-hours collection pipeline.
    """

    last_matcher_run_time = 0
    last_health_heartbeat_time = 0
    last_retention_run_time = 0

    write_pipeline_event(
        "market_pipeline",
        "started",
        "Market pipeline started.",
        {
            "active_symbols": len(SYMBOLS),
            "batch_size": BATCH_SIZE,
            "collection_interval_seconds": COLLECTION_INTERVAL_SECONDS,
            "matcher_interval_seconds": MATCHER_INTERVAL_SECONDS,
            "matcher_valid_window_seconds": MATCHER_VALID_WINDOW_SECONDS,
            "save_csv_backup": SAVE_CSV_BACKUP,
            "health_heartbeat_interval_seconds": HEALTH_HEARTBEAT_INTERVAL_SECONDS,
            "matcher_lookback_hours": MATCHER_LOOKBACK_HOURS,
            "matcher_delayed_padding_seconds": MATCHER_DELAYED_PADDING_SECONDS,
            "raw_retention_days": RAW_RETENTION_DAYS,
            "matched_retention_days": MATCHED_RETENTION_DAYS,
            "retention_interval_seconds": RETENTION_INTERVAL_SECONDS,
            "matched_replica_enabled": bool(MATCHED_REPLICA_DATABASE_URL),
        },
    )

    while True:
        market_is_open, current_time = is_market_open_now()
        current_timestamp = time.time()

        print()
        print("==================================================")
        print("Current Eastern Time:", current_time)
        print("Active Symbols:", len(SYMBOLS))
        print("Batch Size:", BATCH_SIZE)
        print("CSV Backup Enabled:", SAVE_CSV_BACKUP)
        print("Health Heartbeat Seconds:", HEALTH_HEARTBEAT_INTERVAL_SECONDS)
        print("Raw Retention Days:", RAW_RETENTION_DAYS)
        print("Matched Replica Enabled:", bool(MATCHED_REPLICA_DATABASE_URL))

        if market_is_open:
            print("Market is open. Running batch collection...")

            collection_summary = collect_all_symbols_in_batches()
            collection_status = (
                "success"
                if collection_summary["error_count"] == 0
                else "warning"
            )

            write_pipeline_event(
                "collector",
                collection_status,
                "Collection cycle completed.",
                collection_summary,
            )
            write_replica_pipeline_event(
                "collector",
                collection_status,
                "Collection cycle completed.",
                collection_summary,
            )

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

            should_run_matcher = (
                current_timestamp - last_matcher_run_time
            ) >= MATCHER_INTERVAL_SECONDS

            if should_run_matcher:
                print()
                print("Running matcher...")
                try:
                    matcher_summary = run_matcher()

                    write_pipeline_event(
                        "matcher",
                        "success",
                        "Matcher cycle completed.",
                        matcher_summary,
                    )

                    last_matcher_run_time = current_timestamp

                except Exception as error:
                    print("Matcher error:", error)
                    write_pipeline_event(
                        "matcher",
                        "error",
                        str(error),
                    )

            else:
                seconds_until_next_matcher = int(
                    MATCHER_INTERVAL_SECONDS - (
                        current_timestamp - last_matcher_run_time
                    )
                )

                print()
                print("Skipping matcher this cycle.")
                print("Next matcher run in about", seconds_until_next_matcher, "seconds.")

            write_pipeline_event(
                "market_pipeline",
                "running",
                "Market pipeline cycle completed.",
                {
                    "current_eastern_time": current_time.isoformat(),
                    "collection_errors": collection_summary["error_count"],
                },
            )
            write_replica_pipeline_event(
                "market_pipeline",
                "running",
                "Market pipeline cycle completed.",
                {
                    "current_eastern_time": current_time.isoformat(),
                    "collection_errors": collection_summary["error_count"],
                },
            )

            should_run_retention = (
                current_timestamp - last_retention_run_time
            ) >= RETENTION_INTERVAL_SECONDS

            if should_run_retention:
                try:
                    retention_summary = run_retention_cleanup()

                    write_pipeline_event(
                        "retention",
                        "success",
                        "Retention cleanup completed.",
                        retention_summary,
                    )

                    last_retention_run_time = current_timestamp

                except Exception as error:
                    print("Retention cleanup error:", error)
                    write_pipeline_event(
                        "retention",
                        "error",
                        str(error),
                    )

            last_health_heartbeat_time = current_timestamp

        else:
            print("Market is closed. Waiting...")

            should_record_idle_heartbeat = (
                current_timestamp - last_health_heartbeat_time
            ) >= HEALTH_HEARTBEAT_INTERVAL_SECONDS

            if should_record_idle_heartbeat:
                write_pipeline_event(
                    "market_pipeline",
                    "idle",
                    "Market is closed.",
                    {
                        "current_eastern_time": current_time.isoformat(),
                    },
                )
                last_health_heartbeat_time = current_timestamp

        print()
        print("Waiting", COLLECTION_INTERVAL_SECONDS, "seconds...")
        time.sleep(COLLECTION_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
