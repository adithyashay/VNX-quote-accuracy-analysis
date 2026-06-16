import pandas as pd


def safe_mean(series):
    if series.empty:
        return None
    return series.mean()


def safe_median(series):
    if series.empty:
        return None
    return series.median()


def safe_max(series):
    if series.empty:
        return None
    return series.max()


def calculate_overall_metrics(df):
    """
    Calculate high-level accuracy metrics for filtered matched data.
    """

    if df.empty:
        return {
            "total_observations": 0,
            "symbols_analyzed": 0,
            "avg_price_error_pct": None,
            "median_price_error_pct": None,
            "max_price_error_pct": None,
            "avg_directional_error_pct": None,
            "avg_time_gap_seconds": None,
            "earliest_vnx_time": None,
            "latest_vnx_time": None,
        }

    return {
        "total_observations": len(df),
        "symbols_analyzed": df["symbol"].nunique(),
        "avg_price_error_pct": safe_mean(df["absolute_percentage_error"]),
        "median_price_error_pct": safe_median(df["absolute_percentage_error"]),
        "max_price_error_pct": safe_max(df["absolute_percentage_error"]),
        "avg_directional_error_pct": safe_mean(df["percentage_error"]),
        "avg_time_gap_seconds": safe_mean(df["time_gap_seconds"]),
        "earliest_vnx_time": df["vnx_time"].min(),
        "latest_vnx_time": df["vnx_time"].max(),
    }


def calculate_symbol_metrics(df):
    """
    Calculate symbol-level accuracy metrics.
    """

    if df.empty:
        return pd.DataFrame()

    symbol_stats = (
        df.groupby(
            ["symbol", "company_name", "sector", "sub_industry"],
            dropna=False
        )
        .agg(
            observations=("symbol", "count"),
            avg_price_error_pct=("absolute_percentage_error", "mean"),
            median_price_error_pct=("absolute_percentage_error", "median"),
            max_price_error_pct=("absolute_percentage_error", "max"),
            std_price_error_pct=("absolute_percentage_error", "std"),
            avg_directional_error_pct=("percentage_error", "mean"),
            avg_time_gap_seconds=("time_gap_seconds", "mean"),
            earliest_vnx_time=("vnx_time", "min"),
            latest_vnx_time=("vnx_time", "max"),
        )
        .reset_index()
    )

    return symbol_stats.sort_values(
        by=["avg_price_error_pct", "observations"],
        ascending=[True, False]
    )


def calculate_ticker_metrics(df, ticker):
    """
    Calculate metrics for one selected ticker.
    """

    ticker_df = df[df["symbol"] == ticker].copy()

    return calculate_overall_metrics(ticker_df), ticker_df


def calculate_error_threshold_summary(df):
    """
    Calculate percentage of observations within selected error thresholds.
    """

    thresholds = [0.01, 0.05, 0.10, 0.50, 1.00]

    if df.empty:
        return pd.DataFrame(
            {
                "threshold": thresholds,
                "observations": [0 for _ in thresholds],
                "percent_of_observations": [0 for _ in thresholds],
            }
        )

    rows = []
    total = len(df)

    for threshold in thresholds:
        count = (df["absolute_percentage_error"] <= threshold).sum()
        percent = count / total * 100 if total > 0 else 0

        rows.append(
            {
                "threshold": threshold,
                "observations": count,
                "percent_of_observations": percent,
            }
        )

    return pd.DataFrame(rows)


def calculate_raw_coverage_metrics(raw_coverage_df):
    """
    Calculate high-level raw data coverage metrics.
    """

    if raw_coverage_df.empty:
        return {
            "symbols_loaded": 0,
            "symbols_with_vnx": 0,
            "symbols_with_delayed": 0,
            "symbols_with_both": 0,
            "total_vnx_rows": 0,
            "total_delayed_rows": 0,
            "total_matched_rows": 0,
        }

    symbols_with_vnx = (raw_coverage_df["vnx_raw_rows"] > 0).sum()
    symbols_with_delayed = (raw_coverage_df["delayed_raw_rows"] > 0).sum()
    symbols_with_both = (
        (raw_coverage_df["vnx_raw_rows"] > 0)
        & (raw_coverage_df["delayed_raw_rows"] > 0)
    ).sum()

    return {
        "symbols_loaded": len(raw_coverage_df),
        "symbols_with_vnx": symbols_with_vnx,
        "symbols_with_delayed": symbols_with_delayed,
        "symbols_with_both": symbols_with_both,
        "total_vnx_rows": raw_coverage_df["vnx_raw_rows"].sum(),
        "total_delayed_rows": raw_coverage_df["delayed_raw_rows"].sum(),
        "total_matched_rows": raw_coverage_df["matched_rows"].sum(),
    }


def format_percent(value):
    """
    Format percentage values for dashboard display.
    """

    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.4f}%"


def format_number(value):
    """
    Format integer/float numbers for dashboard display.
    """

    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:,.0f}"


def format_float(value, decimals=2):
    """
    Format float values for dashboard display.
    """

    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:,.{decimals}f}"


def prepare_display_table(df):
    """
    Prepare a DataFrame for clean dashboard display.
    """

    if df.empty:
        return df

    display_df = df.copy()

    percent_columns = [
        "avg_price_error_pct",
        "median_price_error_pct",
        "max_price_error_pct",
        "std_price_error_pct",
        "avg_directional_error_pct",
    ]

    for column in percent_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(format_percent)

    if "avg_time_gap_seconds" in display_df.columns:
        display_df["avg_time_gap_seconds"] = display_df[
            "avg_time_gap_seconds"
        ].apply(lambda value: format_float(value, 2))

    return display_df