import pandas as pd


CENTS_THRESHOLDS = [1, 5, 10, 20, 50, 70]
PRICE_BANDS = [
    (0, 50, "< $50"),
    (50, 100, "$50-$100"),
    (100, 250, "$100-$250"),
    (250, 500, "$250-$500"),
    (500, None, ">= $500"),
]


def add_cents_columns(df):
    """
    Add cents-based difference columns from the stored dollar difference.
    """

    if df is None or df.empty or "difference" not in df.columns:
        return df

    enriched_df = df.copy()
    difference = pd.to_numeric(enriched_df["difference"], errors="coerce")

    enriched_df["price_difference_cents"] = difference * 100
    enriched_df["absolute_price_difference_cents"] = (
        enriched_df["price_difference_cents"].abs()
    )

    if "percentage_error" in enriched_df.columns:
        enriched_df["directional_error_bps"] = pd.to_numeric(
            enriched_df["percentage_error"],
            errors="coerce",
        ) * 100

    if "absolute_percentage_error" in enriched_df.columns:
        enriched_df["absolute_error_bps"] = pd.to_numeric(
            enriched_df["absolute_percentage_error"],
            errors="coerce",
        ) * 100

    if "delayed_price" in enriched_df.columns:
        enriched_df["price_band"] = pd.to_numeric(
            enriched_df["delayed_price"],
            errors="coerce",
        ).apply(get_price_band)

    return enriched_df


def get_price_band(price):
    if price is None or pd.isna(price):
        return "Unknown"

    for lower_bound, upper_bound, label in PRICE_BANDS:
        if upper_bound is None and price >= lower_bound:
            return label

        if lower_bound <= price < upper_bound:
            return label

    return "Unknown"


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


def safe_quantile(series, quantile):
    if series.empty:
        return None
    return series.quantile(quantile)


def calculate_overall_metrics(df):
    """
    Calculate high-level accuracy metrics for filtered matched data.
    """

    if df.empty:
        return {
            "total_observations": 0,
            "symbols_analyzed": 0,
            "avg_price_error_cents": None,
            "median_price_error_cents": None,
            "p90_price_error_cents": None,
            "p95_price_error_cents": None,
            "p99_price_error_cents": None,
            "max_price_error_cents": None,
            "avg_directional_error_cents": None,
            "avg_price_error_bps": None,
            "median_price_error_bps": None,
            "p95_price_error_bps": None,
            "avg_directional_error_bps": None,
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
        "avg_price_error_cents": safe_mean(
            df["absolute_price_difference_cents"]
        ),
        "median_price_error_cents": safe_median(
            df["absolute_price_difference_cents"]
        ),
        "p90_price_error_cents": safe_quantile(
            df["absolute_price_difference_cents"],
            0.90,
        ),
        "p95_price_error_cents": safe_quantile(
            df["absolute_price_difference_cents"],
            0.95,
        ),
        "p99_price_error_cents": safe_quantile(
            df["absolute_price_difference_cents"],
            0.99,
        ),
        "max_price_error_cents": safe_max(
            df["absolute_price_difference_cents"]
        ),
        "avg_directional_error_cents": safe_mean(
            df["price_difference_cents"]
        ),
        "avg_price_error_bps": safe_mean(df["absolute_error_bps"]),
        "median_price_error_bps": safe_median(df["absolute_error_bps"]),
        "p95_price_error_bps": safe_quantile(df["absolute_error_bps"], 0.95),
        "avg_directional_error_bps": safe_mean(df["directional_error_bps"]),
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
            avg_price_error_cents=(
                "absolute_price_difference_cents",
                "mean",
            ),
            median_price_error_cents=(
                "absolute_price_difference_cents",
                "median",
            ),
            max_price_error_cents=(
                "absolute_price_difference_cents",
                "max",
            ),
            p95_price_error_cents=(
                "absolute_price_difference_cents",
                lambda series: series.quantile(0.95),
            ),
            std_price_error_cents=(
                "absolute_price_difference_cents",
                "std",
            ),
            avg_directional_error_cents=("price_difference_cents", "mean"),
            avg_price_error_bps=("absolute_error_bps", "mean"),
            median_price_error_bps=("absolute_error_bps", "median"),
            max_price_error_bps=("absolute_error_bps", "max"),
            p95_price_error_bps=(
                "absolute_error_bps",
                lambda series: series.quantile(0.95),
            ),
            avg_directional_error_bps=("directional_error_bps", "mean"),
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
        by=["avg_price_error_cents", "observations"],
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
    Calculate percentage of observations within selected cents thresholds.
    """

    if df.empty:
        return pd.DataFrame(
            {
                "threshold_cents": CENTS_THRESHOLDS,
                "observations": [0 for _ in CENTS_THRESHOLDS],
                "percent_of_observations": [0 for _ in CENTS_THRESHOLDS],
            }
        )

    rows = []
    total = len(df)

    for threshold in CENTS_THRESHOLDS:
        count = (df["absolute_price_difference_cents"] <= threshold).sum()
        percent = count / total * 100 if total > 0 else 0

        rows.append(
            {
                "threshold_cents": threshold,
                "observations": count,
                "percent_of_observations": percent,
            }
        )

    return pd.DataFrame(rows)


def calculate_price_band_summary(df):
    """
    Summarize cents and normalized errors by reference price band.
    """

    columns = [
        "price_band",
        "observations",
        "symbols_analyzed",
        "median_price_error_cents",
        "p95_price_error_cents",
        "max_price_error_cents",
        "median_price_error_bps",
        "p95_price_error_bps",
        "max_price_error_bps",
    ]

    if df.empty:
        return pd.DataFrame(columns=columns)

    band_df = df.copy()

    if "price_band" not in band_df.columns:
        band_df["price_band"] = pd.to_numeric(
            band_df["delayed_price"],
            errors="coerce",
        ).apply(get_price_band)

    summary_df = (
        band_df.groupby("price_band", dropna=False)
        .agg(
            observations=("symbol", "count"),
            symbols_analyzed=("symbol", "nunique"),
            median_price_error_cents=(
                "absolute_price_difference_cents",
                "median",
            ),
            p95_price_error_cents=(
                "absolute_price_difference_cents",
                lambda series: series.quantile(0.95),
            ),
            max_price_error_cents=(
                "absolute_price_difference_cents",
                "max",
            ),
            median_price_error_bps=("absolute_error_bps", "median"),
            p95_price_error_bps=(
                "absolute_error_bps",
                lambda series: series.quantile(0.95),
            ),
            max_price_error_bps=("absolute_error_bps", "max"),
        )
        .reset_index()
    )

    band_order = {label: index for index, (*_, label) in enumerate(PRICE_BANDS)}
    band_order["Unknown"] = len(band_order)
    summary_df["_sort_order"] = summary_df["price_band"].map(band_order)
    summary_df = summary_df.sort_values("_sort_order").drop(columns="_sort_order")

    return summary_df[columns]


def calculate_observation_interval_summary(df, interval_minutes=5):
    """
    Count matched observations by VNX collection-time bucket.
    """

    columns = [
        "interval_start",
        "interval_end",
        "observations",
        "symbols_analyzed",
        "avg_price_error_cents",
        "max_price_error_cents",
        "avg_time_gap_seconds",
    ]

    if df.empty:
        return pd.DataFrame(columns=columns)

    interval_minutes = max(int(interval_minutes), 1)
    interval_df = df.copy()
    interval_df["vnx_time"] = pd.to_datetime(
        interval_df["vnx_time"],
        errors="coerce",
    )
    interval_df = interval_df.dropna(subset=["vnx_time"])

    if interval_df.empty:
        return pd.DataFrame(columns=columns)

    interval_df["interval_start"] = interval_df["vnx_time"].dt.floor(
        f"{interval_minutes}min"
    )

    summary_df = (
        interval_df.groupby("interval_start", dropna=False)
        .agg(
            observations=("symbol", "count"),
            symbols_analyzed=("symbol", "nunique"),
            avg_price_error_cents=(
                "absolute_price_difference_cents",
                "mean",
            ),
            max_price_error_cents=(
                "absolute_price_difference_cents",
                "max",
            ),
            avg_time_gap_seconds=("time_gap_seconds", "mean"),
        )
        .reset_index()
        .sort_values("interval_start")
    )

    summary_df["interval_end"] = summary_df["interval_start"] + pd.to_timedelta(
        interval_minutes,
        unit="min",
    )

    return summary_df[columns]


def calculate_data_coverage_metrics(data_coverage_df):
    """
    Calculate high-level matched-first data coverage metrics.
    """

    if data_coverage_df.empty:
        return {
            "symbols_loaded": 0,
            "symbols_with_vnx": 0,
            "symbols_with_delayed": 0,
            "symbols_with_both": 0,
            "symbols_with_matched": 0,
            "total_vnx_rows": 0,
            "total_delayed_rows": 0,
            "total_matched_rows": 0,
            "latest_matched_time": None,
        }

    symbols_with_vnx = (data_coverage_df["vnx_raw_rows"] > 0).sum()
    symbols_with_delayed = (data_coverage_df["delayed_raw_rows"] > 0).sum()
    symbols_with_both = (
        (data_coverage_df["vnx_raw_rows"] > 0)
        & (data_coverage_df["delayed_raw_rows"] > 0)
    ).sum()

    return {
        "symbols_loaded": len(data_coverage_df),
        "symbols_with_vnx": symbols_with_vnx,
        "symbols_with_delayed": symbols_with_delayed,
        "symbols_with_both": symbols_with_both,
        "symbols_with_matched": (data_coverage_df["matched_rows"] > 0).sum(),
        "total_vnx_rows": data_coverage_df["vnx_raw_rows"].sum(),
        "total_delayed_rows": data_coverage_df["delayed_raw_rows"].sum(),
        "total_matched_rows": data_coverage_df["matched_rows"].sum(),
        "latest_matched_time": data_coverage_df["latest_matched_time"].max()
        if "latest_matched_time" in data_coverage_df.columns
        else None,
    }


def format_percent(value):
    """
    Format percentage values for dashboard display.
    """

    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.4f}%"


def format_cents(value, decimals=2):
    """
    Format cents values for dashboard display.
    """

    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:,.{decimals}f} cents"


def format_signed_cents(value, decimals=2):
    """
    Format signed cents values for directional differences.
    """

    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:+,.{decimals}f} cents"


def format_bps(value, decimals=2):
    """
    Format basis-point values for price-normalized display.
    """

    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:,.{decimals}f} bps"


def format_signed_bps(value, decimals=2):
    """
    Format signed basis-point values for directional differences.
    """

    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:+,.{decimals}f} bps"


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

    signed_cents_columns = [
        "avg_directional_error_cents",
        "price_difference_cents",
    ]

    cents_columns = [
        "avg_price_error_cents",
        "median_price_error_cents",
        "p90_price_error_cents",
        "p95_price_error_cents",
        "p99_price_error_cents",
        "max_price_error_cents",
        "std_price_error_cents",
        "absolute_price_difference_cents",
    ]

    signed_bps_columns = [
        "avg_directional_error_bps",
        "directional_error_bps",
    ]

    bps_columns = [
        "avg_price_error_bps",
        "median_price_error_bps",
        "max_price_error_bps",
        "p95_price_error_bps",
        "absolute_error_bps",
    ]

    for column in signed_cents_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(format_signed_cents)

    for column in cents_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(format_cents)

    for column in signed_bps_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(format_signed_bps)

    for column in bps_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(format_bps)

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
