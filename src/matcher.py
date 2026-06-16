import os
import pandas as pd


VNX_HISTORY_FILE = "data/raw/vnx_quote_history.csv"
DELAYED_HISTORY_FILE = "data/raw/delayed_quote_history.csv"
MATCHED_ANALYSIS_FILE = "data/processed/matched_quote_analysis.csv"


def load_raw_quote_data():
    """
    Load raw VNX quote history and delayed quote history.
    Parse mixed timestamp formats safely.
    """

    vnx_df = pd.read_csv(VNX_HISTORY_FILE, low_memory=False)
    delayed_df = pd.read_csv(DELAYED_HISTORY_FILE, low_memory=False)

    vnx_df["timestamp_readable"] = pd.to_datetime(
        vnx_df["timestamp_readable"],
        format="mixed",
        errors="coerce"
    )

    delayed_df["delayed_time_readable"] = pd.to_datetime(
        delayed_df["delayed_time_readable"],
        format="mixed",
        errors="coerce"
    )

    vnx_df = vnx_df.dropna(subset=["timestamp_readable"])
    delayed_df = delayed_df.dropna(subset=["delayed_time_readable"])

    return vnx_df, delayed_df


def load_existing_matched_data():
    """
    Load existing matched analysis if it exists.
    """

    if os.path.exists(MATCHED_ANALYSIS_FILE) and os.path.getsize(MATCHED_ANALYSIS_FILE) > 0:
        existing_df = pd.read_csv(MATCHED_ANALYSIS_FILE)

        existing_df["vnx_time"] = pd.to_datetime(
            existing_df["vnx_time"],
            format="mixed",
            errors="coerce"
        )

        existing_df["delayed_time"] = pd.to_datetime(
            existing_df["delayed_time"],
            format="mixed",
            errors="coerce"
        )

        existing_df = existing_df.dropna(subset=["vnx_time", "delayed_time"])

        return existing_df

    return pd.DataFrame()


def create_vnx_match_key(df, symbol_column="symbol", time_column="timestamp_readable"):
    """
    Create a unique key for each VNX quote row.

    This key tells us whether a VNX quote has already been matched.
    """

    return (
        df[symbol_column].astype(str)
        + "|"
        + df[time_column].astype(str)
    )


def filter_unmatched_vnx_rows(vnx_df, existing_matched_df):
    """
    Keep only VNX rows that have not already been matched.
    """

    if existing_matched_df.empty:
        return vnx_df

    vnx_df = vnx_df.copy()
    existing_matched_df = existing_matched_df.copy()

    vnx_df["match_key"] = create_vnx_match_key(
        vnx_df,
        symbol_column="symbol",
        time_column="timestamp_readable"
    )

    existing_matched_df["match_key"] = create_vnx_match_key(
        existing_matched_df,
        symbol_column="symbol",
        time_column="vnx_time"
    )

    existing_keys = set(existing_matched_df["match_key"])

    unmatched_vnx_df = vnx_df[
        ~vnx_df["match_key"].isin(existing_keys)
    ].copy()

    unmatched_vnx_df = unmatched_vnx_df.drop(columns=["match_key"])

    return unmatched_vnx_df


def calculate_error_columns(matched_df):
    """
    Add difference, percentage error, and absolute percentage error.
    """

    matched_df["difference"] = (
        matched_df["vnx_price"] - matched_df["delayed_price"]
    )

    matched_df["percentage_error"] = (
        matched_df["difference"] / matched_df["delayed_price"]
    ) * 100

    matched_df["absolute_percentage_error"] = (
        matched_df["percentage_error"].abs()
    )

    matched_df["difference"] = matched_df["difference"].round(4)
    matched_df["percentage_error"] = matched_df["percentage_error"].round(4)
    matched_df["absolute_percentage_error"] = matched_df[
        "absolute_percentage_error"
    ].round(4)

    return matched_df


def match_vnx_rows_to_delayed(vnx_df, delayed_df, valid_window_seconds=60):
    """
    Match provided VNX rows to delayed/reference rows using nearest timestamp.
    """

    if vnx_df.empty or delayed_df.empty:
        return pd.DataFrame()

    vnx_df = vnx_df[
        [
            "symbol",
            "vnx_price",
            "timestamp_readable"
        ]
    ].copy()

    delayed_df = delayed_df[
        [
            "symbol",
            "delayed_price",
            "delayed_time_readable"
        ]
    ].copy()

    matched_groups = []

    for symbol, symbol_vnx_df in vnx_df.groupby("symbol"):
        symbol_delayed_df = delayed_df[delayed_df["symbol"] == symbol]

        if symbol_delayed_df.empty:
            continue

        symbol_vnx_df = symbol_vnx_df.sort_values("timestamp_readable")
        symbol_delayed_df = symbol_delayed_df.sort_values("delayed_time_readable")

        matched_symbol_df = pd.merge_asof(
            symbol_vnx_df,
            symbol_delayed_df,
            left_on="timestamp_readable",
            right_on="delayed_time_readable",
            direction="nearest",
            suffixes=("", "_delayed")
        )

        matched_groups.append(matched_symbol_df)

    if not matched_groups:
        return pd.DataFrame()

    matched_df = pd.concat(matched_groups, ignore_index=True)

    matched_df = matched_df.dropna(subset=["delayed_price"])

    matched_df["time_gap_seconds"] = (
        matched_df["timestamp_readable"] - matched_df["delayed_time_readable"]
    ).abs().dt.total_seconds()

    matched_df["valid_match"] = (
        matched_df["time_gap_seconds"] <= valid_window_seconds
    )

    matched_df = calculate_error_columns(matched_df)

    matched_df = matched_df.rename(
        columns={
            "timestamp_readable": "vnx_time",
            "delayed_time_readable": "delayed_time"
        }
    )

    matched_df = matched_df[
        [
            "symbol",
            "vnx_price",
            "vnx_time",
            "delayed_price",
            "delayed_time",
            "time_gap_seconds",
            "valid_match",
            "difference",
            "percentage_error",
            "absolute_percentage_error"
        ]
    ]

    return matched_df


def match_all_vnx_quotes_to_delayed(valid_window_seconds=60, incremental=True):
    """
    Main matcher function.

    If incremental=True:
        only match VNX rows that have not already been matched.

    If incremental=False:
        rebuild matches from all raw VNX rows.
    """

    vnx_df, delayed_df = load_raw_quote_data()

    if vnx_df.empty or delayed_df.empty:
        return pd.DataFrame()

    if incremental:
        existing_matched_df = load_existing_matched_data()
        vnx_df = filter_unmatched_vnx_rows(vnx_df, existing_matched_df)

    matched_df = match_vnx_rows_to_delayed(
        vnx_df=vnx_df,
        delayed_df=delayed_df,
        valid_window_seconds=valid_window_seconds
    )

    return matched_df


def save_matched_results(matched_df):
    """
    Save matched results into processed CSV.

    Duplicate rule:
    Same symbol + same VNX time should only exist once.
    """

    if matched_df.empty:
        return {
            "saved_rows": 0,
            "reason": "No matched results to save"
        }

    if os.path.exists(MATCHED_ANALYSIS_FILE) and os.path.getsize(MATCHED_ANALYSIS_FILE) > 0:
        existing_df = pd.read_csv(MATCHED_ANALYSIS_FILE)

        combined_df = pd.concat(
            [existing_df, matched_df],
            ignore_index=True
        )

        before_dedup_count = len(combined_df)

        combined_df = combined_df.drop_duplicates(
            subset=["symbol", "vnx_time"],
            keep="first"
        )

        after_dedup_count = len(combined_df)

        saved_rows = after_dedup_count - len(existing_df)

    else:
        combined_df = matched_df.drop_duplicates(
            subset=["symbol", "vnx_time"],
            keep="first"
        )

        saved_rows = len(combined_df)

    combined_df.to_csv(MATCHED_ANALYSIS_FILE, index=False)

    return {
        "saved_rows": saved_rows,
        "reason": "Matched results saved"
    }