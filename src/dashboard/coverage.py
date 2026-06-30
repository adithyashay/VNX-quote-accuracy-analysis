import json

import pandas as pd


PROBLEM_DESCRIPTIONS = {
    "api_error": "API request failed for the symbol batch.",
    "missing_from_response": "The symbol was requested but was not returned.",
    "missing_price": "The symbol was returned without a usable price.",
    "missing_timestamp": "The symbol was returned without a usable timestamp.",
    "stale_timestamp": (
        "The symbol was returned, but its quote timestamp is older than the "
        "configured freshness threshold."
    ),
    "unexpected_symbol": "The API returned a symbol that was not requested.",
}


def normalize_event_details(details):
    if isinstance(details, dict):
        return details

    if isinstance(details, str):
        try:
            parsed_details = json.loads(details)
        except json.JSONDecodeError:
            return {}

        if isinstance(parsed_details, dict):
            return parsed_details

    return {}


def build_collection_coverage_tables(history_df):
    coverage_rows = []
    problem_rows = []

    if history_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    for _, event in history_df.iterrows():
        event_time = pd.to_datetime(event.get("event_time"), errors="coerce")
        details = normalize_event_details(event.get("details"))
        cycle_started_at = pd.to_datetime(
            details.get("cycle_started_at", event_time),
            errors="coerce",
        )
        snapshot_coverage = details.get("snapshot_coverage", {})

        for source in ["vnx", "delayed"]:
            source_summary = snapshot_coverage.get(source)

            if not source_summary:
                continue

            coverage_rows.append(
                {
                    "event_time": event_time,
                    "cycle_started_at": cycle_started_at,
                    "source": source.upper(),
                    "status": event.get("status"),
                    "requested_count": source_summary.get("requested_count"),
                    "returned_count": source_summary.get("returned_count"),
                    "ok_count": source_summary.get("ok_count"),
                    "problem_count": source_summary.get("problem_count"),
                    "missing_count": source_summary.get("missing_count"),
                    "source_timestamp_min": source_summary.get(
                        "source_timestamp_min"
                    ),
                    "source_timestamp_max": source_summary.get(
                        "source_timestamp_max"
                    ),
                }
            )

            symbols_by_status = source_summary.get("symbols_by_status", {})

            for problem_status, symbols in symbols_by_status.items():
                for symbol in symbols:
                    problem_rows.append(
                        {
                            "event_time": event_time,
                            "cycle_started_at": cycle_started_at,
                            "source": source.upper(),
                            "problem": problem_status,
                            "reason": PROBLEM_DESCRIPTIONS.get(
                                problem_status,
                                problem_status,
                            ),
                            "symbol": symbol,
                        }
                    )

    return pd.DataFrame(coverage_rows), pd.DataFrame(problem_rows)


def calculate_collection_cycle_metrics(
    coverage_df,
    expected_interval_seconds=60,
    cadence_warning_seconds=120,
):
    """
    Calculate actual polling cadence from collector coverage summaries.
    """

    cadence_warning_seconds = max(
        int(cadence_warning_seconds),
        int(expected_interval_seconds),
    )

    if coverage_df.empty or "cycle_started_at" not in coverage_df.columns:
        return {
            "first_cycle": None,
            "latest_cycle": None,
            "actual_cycles": 0,
            "cadence_warning_seconds": cadence_warning_seconds,
            "late_gap_count": 0,
            "potential_missed_cycles": 0,
            "avg_cycle_gap_seconds": None,
            "p95_cycle_gap_seconds": None,
            "max_cycle_gap_seconds": None,
        }

    cycle_times = (
        pd.to_datetime(coverage_df["cycle_started_at"], errors="coerce")
        .dropna()
        .drop_duplicates()
        .sort_values()
    )

    if cycle_times.empty:
        return {
            "first_cycle": None,
            "latest_cycle": None,
            "actual_cycles": 0,
            "cadence_warning_seconds": cadence_warning_seconds,
            "late_gap_count": 0,
            "potential_missed_cycles": 0,
            "avg_cycle_gap_seconds": None,
            "p95_cycle_gap_seconds": None,
            "max_cycle_gap_seconds": None,
        }

    actual_cycles = len(cycle_times)
    first_cycle = cycle_times.iloc[0]
    latest_cycle = cycle_times.iloc[-1]
    cycle_gaps = cycle_times.diff().dt.total_seconds().dropna()
    late_gaps = cycle_gaps[cycle_gaps > cadence_warning_seconds]
    potential_missed_cycles = int(
        sum(max(int(gap // cadence_warning_seconds) - 1, 0) for gap in late_gaps)
    )

    return {
        "first_cycle": first_cycle,
        "latest_cycle": latest_cycle,
        "actual_cycles": actual_cycles,
        "cadence_warning_seconds": cadence_warning_seconds,
        "late_gap_count": len(late_gaps),
        "potential_missed_cycles": potential_missed_cycles,
        "avg_cycle_gap_seconds": cycle_gaps.mean()
        if not cycle_gaps.empty
        else None,
        "p95_cycle_gap_seconds": cycle_gaps.quantile(0.95)
        if not cycle_gaps.empty
        else None,
        "max_cycle_gap_seconds": cycle_gaps.max()
        if not cycle_gaps.empty
        else None,
    }


def calculate_problem_summary(problem_df):
    if problem_df.empty:
        return pd.DataFrame(
            columns=[
                "source",
                "problem",
                "reason",
                "problem_snapshots",
                "symbols_impacted",
                "latest_problem_time",
            ]
        )

    return (
        problem_df.groupby(["source", "problem", "reason"], dropna=False)
        .agg(
            problem_snapshots=("problem", "count"),
            symbols_impacted=("symbol", "nunique"),
            latest_problem_time=("event_time", "max"),
        )
        .reset_index()
        .sort_values(
            ["problem_snapshots", "symbols_impacted"],
            ascending=[False, False],
        )
    )


def calculate_repeated_problem_symbols(problem_df):
    if problem_df.empty:
        return pd.DataFrame(
            columns=[
                "source",
                "symbol",
                "problem_count",
                "problem_types",
                "latest_problem_time",
            ]
        )

    grouped_df = (
        problem_df.groupby(["source", "symbol"], dropna=False)
        .agg(
            problem_count=("problem", "count"),
            problem_types=("problem", lambda values: ", ".join(sorted(set(values)))),
            latest_problem_time=("event_time", "max"),
        )
        .reset_index()
        .sort_values(
            ["problem_count", "latest_problem_time"],
            ascending=[False, False],
        )
    )

    return grouped_df
