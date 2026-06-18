import os
import pandas as pd


MATCHED_ANALYSIS_FILE = "data/processed/matched_quote_analysis.csv"


def normalize_datetime_series(series):
    """
    Parse timestamp values into a consistent pandas datetime series.
    """

    return pd.to_datetime(
        series,
        format="mixed",
        errors="coerce"
    )


def normalize_timestamp_key(series):
    """
    Normalize timestamps before using them as de-duplication keys.

    String casting is not safe here because pandas may serialize equivalent
    timestamps as either `.544` or `.544000`.
    """

    normalized = normalize_datetime_series(series)

    return normalized.dt.strftime("%Y-%m-%d %H:%M:%S.%f")


def normalize_matched_dataframe(matched_df):
    """
    Normalize matched-analysis timestamps and keep the closest row per VNX quote.
    """

    if matched_df.empty:
        return matched_df

    matched_df = matched_df.copy()

    for column in ["vnx_time", "delayed_time"]:
        if column in matched_df.columns:
            matched_df[column] = normalize_datetime_series(matched_df[column])

    matched_df = matched_df.dropna(subset=["vnx_time"])

    if "time_gap_seconds" in matched_df.columns:
        matched_df = matched_df.sort_values(
            by=["symbol", "vnx_time", "time_gap_seconds"],
            ascending=[True, True, True],
        )
    else:
        matched_df = matched_df.sort_values(
            by=["symbol", "vnx_time"],
            ascending=[True, True],
        )

    return matched_df.drop_duplicates(
        subset=["symbol", "vnx_time"],
        keep="first"
    )


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
        existing_df = normalize_matched_dataframe(existing_df)
        matched_df = normalize_matched_dataframe(matched_df)

        combined_df = pd.concat(
            [existing_df, matched_df],
            ignore_index=True
        )

        combined_df = normalize_matched_dataframe(combined_df)

        after_dedup_count = len(combined_df)

        saved_rows = after_dedup_count - len(existing_df)

    else:
        combined_df = normalize_matched_dataframe(matched_df)

        saved_rows = len(combined_df)

    combined_df.to_csv(
        MATCHED_ANALYSIS_FILE,
        index=False,
        date_format="%Y-%m-%d %H:%M:%S.%f",
    )

    return {
        "saved_rows": saved_rows,
        "reason": "Matched results saved"
    }
