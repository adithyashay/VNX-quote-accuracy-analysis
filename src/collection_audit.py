from datetime import datetime

import pandas as pd


def normalize_symbol(value):
    if value is None or pd.isna(value):
        return ""

    return str(value).strip().upper()


def normalize_datetime(value):
    if value is None or pd.isna(value):
        return None

    timestamp = pd.to_datetime(value, errors="coerce")

    if pd.isna(timestamp):
        return None

    return timestamp.to_pydatetime()


def normalize_number(value):
    if value is None or pd.isna(value):
        return None

    return float(value)


def calculate_age_seconds(collected_at, source_timestamp):
    if collected_at is None or source_timestamp is None:
        return None

    return (collected_at - source_timestamp).total_seconds()


def build_snapshot_audit_rows(
    source,
    requested_symbols,
    returned_rows,
    cycle_id,
    batch_number,
    timestamp_field,
    price_field,
    error_message=None,
    stale_after_seconds=None,
):
    """
    Build one audit row per requested symbol for one API polling attempt.
    """

    cycle_time = normalize_datetime(cycle_id) or datetime.now()
    requested = [normalize_symbol(symbol) for symbol in requested_symbols]
    requested = [symbol for symbol in requested if symbol]

    returned_by_symbol = {}

    for row in returned_rows or []:
        symbol = normalize_symbol(row.get("symbol"))

        if symbol and symbol not in returned_by_symbol:
            returned_by_symbol[symbol] = row

    audit_rows = []

    for symbol in requested:
        returned_row = returned_by_symbol.get(symbol)

        if error_message:
            audit_rows.append(
                {
                    "cycle_id": cycle_time,
                    "source": source,
                    "symbol": symbol,
                    "requested": True,
                    "returned": False,
                    "source_timestamp": None,
                    "collected_at": cycle_time,
                    "source_age_seconds": None,
                    "price": None,
                    "status": "api_error",
                    "reason": str(error_message),
                    "batch_number": batch_number,
                }
            )
            continue

        if returned_row is None:
            audit_rows.append(
                {
                    "cycle_id": cycle_time,
                    "source": source,
                    "symbol": symbol,
                    "requested": True,
                    "returned": False,
                    "source_timestamp": None,
                    "collected_at": cycle_time,
                    "source_age_seconds": None,
                    "price": None,
                    "status": "missing_from_response",
                    "reason": "Symbol was requested but not returned by the API.",
                    "batch_number": batch_number,
                }
            )
            continue

        source_timestamp = normalize_datetime(returned_row.get(timestamp_field))
        price = normalize_number(returned_row.get(price_field))
        source_age_seconds = calculate_age_seconds(cycle_time, source_timestamp)

        missing_timestamp = source_timestamp is None
        missing_price = price is None
        stale_timestamp = (
            stale_after_seconds is not None
            and source_age_seconds is not None
            and source_age_seconds > stale_after_seconds
        )

        if missing_timestamp:
            status = "missing_timestamp"
            reason = "API returned the symbol without a usable timestamp."
        elif missing_price:
            status = "missing_price"
            reason = "API returned the symbol without a usable price."
        elif stale_timestamp:
            status = "stale_timestamp"
            reason = (
                "API returned the symbol, but the source timestamp is older "
                f"than {stale_after_seconds} seconds."
            )
        else:
            status = "ok"
            reason = None

        audit_rows.append(
            {
                "cycle_id": cycle_time,
                "source": source,
                "symbol": symbol,
                "requested": True,
                "returned": True,
                "source_timestamp": source_timestamp,
                "collected_at": cycle_time,
                "source_age_seconds": source_age_seconds,
                "price": price,
                "status": status,
                "reason": reason,
                "batch_number": batch_number,
            }
        )

    requested_set = set(requested)

    for symbol, returned_row in returned_by_symbol.items():
        if symbol in requested_set:
            continue

        source_timestamp = normalize_datetime(returned_row.get(timestamp_field))
        price = normalize_number(returned_row.get(price_field))

        audit_rows.append(
            {
                "cycle_id": cycle_time,
                "source": source,
                "symbol": symbol,
                "requested": False,
                "returned": True,
                "source_timestamp": source_timestamp,
                "collected_at": cycle_time,
                "source_age_seconds": calculate_age_seconds(
                    cycle_time,
                    source_timestamp,
                ),
                "price": price,
                "status": "unexpected_symbol",
                "reason": "API returned a symbol that was not requested.",
                "batch_number": batch_number,
            }
        )

    return audit_rows


def summarize_snapshot_audit_rows(audit_rows):
    """
    Summarize audit rows by source for pipeline health and Streamlit Cloud.
    """

    summary = {}

    for source in sorted({row["source"] for row in audit_rows}):
        source_rows = [row for row in audit_rows if row["source"] == source]
        requested_rows = [row for row in source_rows if row["requested"]]
        returned_rows = [row for row in requested_rows if row["returned"]]
        problem_rows = [
            row for row in source_rows
            if row["status"] != "ok"
        ]
        source_timestamps = [
            row["source_timestamp"]
            for row in returned_rows
            if row["source_timestamp"] is not None
        ]

        status_counts = {}
        symbols_by_status = {}

        for row in problem_rows:
            status = row["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
            symbols_by_status.setdefault(status, []).append(row["symbol"])

        summary[source] = {
            "requested_count": len(requested_rows),
            "returned_count": len(returned_rows),
            "ok_count": len([row for row in requested_rows if row["status"] == "ok"]),
            "problem_count": len(problem_rows),
            "missing_count": len(
                [row for row in requested_rows if not row["returned"]]
            ),
            "status_counts": status_counts,
            "symbols_by_status": symbols_by_status,
            "source_timestamp_min": min(source_timestamps)
            if source_timestamps
            else None,
            "source_timestamp_max": max(source_timestamps)
            if source_timestamps
            else None,
        }

    return summary
