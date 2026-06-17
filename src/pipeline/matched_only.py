import pandas as pd

from config.symbols import ACTIVE_SYMBOLS
from src.batch_collectors import (
    collect_delayed_quotes_batch,
    collect_vnx_quotes_batch,
)
from src.database.connection import get_connection
from src.database.pipeline_health import record_pipeline_event
from src.database.writer import insert_matched_quote_rows
from src.market_hours import is_market_open_now
from src.matcher import match_vnx_rows_to_delayed, normalize_matched_dataframe
from src.settings import get_int_env


def split_into_batches(items, batch_size):
    for index in range(0, len(items), batch_size):
        yield items[index:index + batch_size]


def safe_record_pipeline_event(component, status, message=None, details=None):
    try:
        record_pipeline_event(
            component=component,
            status=status,
            message=message,
            details=details,
        )
    except Exception as error:
        print("Pipeline health event failed:", error)


def build_empty_cycle_summary(market_is_open, current_time, symbol_count):
    return {
        "market_is_open": market_is_open,
        "current_eastern_time": current_time.isoformat(),
        "symbols_requested": symbol_count,
        "vnx_rows_collected": 0,
        "delayed_rows_collected": 0,
        "matched_rows_generated": 0,
        "matched_rows_inserted": 0,
        "valid_matches": 0,
        "invalid_matches": 0,
        "batch_errors": 0,
        "pruned_rows": 0,
    }


def summarize_matched_rows(matched_df):
    if matched_df.empty:
        return 0, 0

    valid_matches = int((matched_df["valid_match"] == True).sum())
    invalid_matches = int(len(matched_df) - valid_matches)

    return valid_matches, invalid_matches


def prune_old_matched_rows(retention_days):
    if retention_days is None or retention_days <= 0:
        return 0

    query = """
        DELETE FROM matched_quote_analysis
        WHERE vnx_time < (
            CURRENT_DATE - (%s * INTERVAL '1 day')
        );
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (retention_days,))
            deleted_rows = cursor.rowcount

        connection.commit()

    return deleted_rows


def run_matched_only_cycle(
    symbols=None,
    batch_size=None,
    valid_window_seconds=None,
    retention_days=None,
):
    symbols = list(symbols or ACTIVE_SYMBOLS)
    batch_size = batch_size or get_int_env("BATCH_SIZE", 100, min_value=1)
    valid_window_seconds = valid_window_seconds or get_int_env(
        "MATCHER_VALID_WINDOW_SECONDS",
        60,
        min_value=1,
    )
    retention_days = (
        get_int_env("MATCHED_RETENTION_DAYS", 0, min_value=0)
        if retention_days is None
        else retention_days
    )

    market_is_open, current_time = is_market_open_now()
    summary = build_empty_cycle_summary(
        market_is_open=market_is_open,
        current_time=current_time,
        symbol_count=len(symbols),
    )

    if not market_is_open:
        print("Market is closed. Scheduled matched-only cycle skipped.")
        safe_record_pipeline_event(
            "scheduled_matched_pipeline",
            "idle",
            "Market is closed. Cycle skipped.",
            summary,
        )
        return summary

    print("Market is open. Running scheduled matched-only cycle.")
    print("Active symbols:", len(symbols))
    print("Batch size:", batch_size)
    print("Valid match window seconds:", valid_window_seconds)

    for batch_number, symbol_batch in enumerate(
        split_into_batches(symbols, batch_size),
        start=1,
    ):
        print()
        print(f"Collecting and matching batch {batch_number}: {len(symbol_batch)} symbols")

        try:
            vnx_status = collect_vnx_quotes_batch(
                symbol_batch,
                save_csv_backup=False,
            )
            delayed_status = collect_delayed_quotes_batch(
                symbol_batch,
                save_csv_backup=False,
            )

            vnx_rows = vnx_status.get("rows", [])
            delayed_rows = delayed_status.get("rows", [])

            summary["vnx_rows_collected"] += len(vnx_rows)
            summary["delayed_rows_collected"] += len(delayed_rows)

            matched_df = match_vnx_rows_to_delayed(
                vnx_df=pd.DataFrame(vnx_rows),
                delayed_df=pd.DataFrame(delayed_rows),
                valid_window_seconds=valid_window_seconds,
            )
            matched_df = normalize_matched_dataframe(matched_df)

            inserted_rows = insert_matched_quote_rows(matched_df)
            valid_matches, invalid_matches = summarize_matched_rows(matched_df)

            summary["matched_rows_generated"] += len(matched_df)
            summary["matched_rows_inserted"] += inserted_rows
            summary["valid_matches"] += valid_matches
            summary["invalid_matches"] += invalid_matches

            print("VNX rows collected:", len(vnx_rows))
            print("Delayed rows collected:", len(delayed_rows))
            print("Matched rows inserted:", inserted_rows)

        except Exception as error:
            summary["batch_errors"] += 1
            print("Batch error:", error)
            safe_record_pipeline_event(
                "scheduled_matched_pipeline",
                "error",
                str(error),
                {
                    "batch_number": batch_number,
                    "symbols": symbol_batch,
                },
            )

    summary["pruned_rows"] = prune_old_matched_rows(retention_days)
    cycle_status = "success" if summary["batch_errors"] == 0 else "warning"

    safe_record_pipeline_event(
        "scheduled_matched_pipeline",
        cycle_status,
        "Scheduled matched-only cycle completed.",
        summary,
    )

    print()
    print("Scheduled Matched-Only Summary")
    print("------------------------------")

    for key, value in summary.items():
        print(f"{key}: {value}")

    return summary
