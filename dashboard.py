from datetime import timedelta

import pandas as pd
import streamlit as st

from src.settings import get_int_env
from src.dashboard.auth import require_dashboard_login
from src.dashboard.queries import (
    get_available_date_range,
    get_symbols,
    get_sectors,
    load_matched_data,
    load_pipeline_health_summary,
    load_data_coverage,
    load_timestamp_window_summary,
    load_collection_coverage_history,
)
from src.dashboard.coverage import (
    build_collection_coverage_tables,
    calculate_collection_cycle_metrics,
    calculate_problem_summary,
    calculate_repeated_problem_symbols,
)
from src.dashboard.metrics import (
    calculate_overall_metrics,
    calculate_symbol_metrics,
    calculate_ticker_metrics,
    calculate_error_threshold_summary,
    calculate_price_band_summary,
    calculate_observation_interval_summary,
    calculate_data_coverage_metrics,
    prepare_display_table,
    format_percent,
    format_cents,
    format_signed_cents,
    format_bps,
    format_signed_bps,
    format_number,
    format_float,
)
from src.dashboard.charts import (
    create_price_comparison_chart,
    create_absolute_error_over_time_chart,
    create_directional_error_over_time_chart,
    create_time_gap_over_time_chart,
    create_worst_symbols_chart,
    create_best_symbols_chart,
    create_directional_error_by_symbol_chart,
    create_observation_count_chart,
    create_error_threshold_chart,
    create_timestamp_window_chart,
    create_observation_interval_chart,
    create_price_band_chart,
    create_window_observation_chart,
)
from src.dashboard.exports import (
    dataframe_to_csv_bytes,
    clean_export_dataframe,
    build_export_filename,
)
from src.dashboard.health import (
    calculate_freshness_status,
    format_age,
    format_timestamp,
    get_latest_component_event,
)
from src.dashboard.styles import (
    apply_page_config,
    apply_custom_styles,
    render_header,
    render_methodology_note,
)


COLLECTION_INTERVAL_SECONDS = get_int_env(
    "COLLECTION_INTERVAL_SECONDS",
    60,
    min_value=1,
)
COLLECTION_CADENCE_WARNING_SECONDS = get_int_env(
    "COLLECTION_CADENCE_WARNING_SECONDS",
    max(COLLECTION_INTERVAL_SECONDS * 2, COLLECTION_INTERVAL_SECONDS + 60),
    min_value=COLLECTION_INTERVAL_SECONDS,
)
MATCHER_INTERVAL_SECONDS = get_int_env(
    "MATCHER_INTERVAL_SECONDS",
    300,
    min_value=1,
)


@st.cache_data(ttl=300)
def cached_symbols():
    return get_symbols()


@st.cache_data(ttl=300)
def cached_sectors():
    return get_sectors()


@st.cache_data(ttl=300)
def cached_date_range():
    return get_available_date_range()


@st.cache_data(ttl=300)
def cached_matched_data(
    start_date,
    end_date,
    selected_symbols,
    selected_sectors,
    max_time_gap_seconds,
    valid_only,
):
    return load_matched_data(
        start_date=start_date,
        end_date=end_date,
        selected_symbols=selected_symbols,
        selected_sectors=selected_sectors,
        max_time_gap_seconds=max_time_gap_seconds,
        valid_only=valid_only,
    )


@st.cache_data(ttl=300)
def cached_data_coverage():
    return load_data_coverage()


@st.cache_data(ttl=300)
def cached_window_summary(
    start_date,
    end_date,
    selected_symbols,
    selected_sectors,
):
    return load_timestamp_window_summary(
        start_date=start_date,
        end_date=end_date,
        selected_symbols=selected_symbols,
        selected_sectors=selected_sectors,
    )


@st.cache_data(ttl=60)
def cached_pipeline_health():
    return load_pipeline_health_summary()


@st.cache_data(ttl=60)
def cached_collection_coverage_history():
    return load_collection_coverage_history(limit=500)


def calculate_dashboard_stale_symbol_summary(problem_df, coverage_df, source="VNX"):
    columns = [
        "source",
        "symbol",
        "stale_snapshots",
        "recent_cycles_analyzed",
        "stale_snapshot_pct",
        "first_stale_time",
        "latest_stale_time",
    ]

    if problem_df.empty:
        return pd.DataFrame(columns=columns)

    source = source.upper()
    source_problem_df = problem_df[
        (problem_df["source"] == source)
        & (problem_df["problem"] == "stale_timestamp")
    ].copy()

    if source_problem_df.empty:
        return pd.DataFrame(columns=columns)

    if coverage_df.empty or "cycle_started_at" not in coverage_df.columns:
        recent_cycles_analyzed = 0
    else:
        source_coverage_df = coverage_df[coverage_df["source"] == source]
        recent_cycles_analyzed = (
            pd.to_datetime(
                source_coverage_df["cycle_started_at"],
                errors="coerce",
            )
            .dropna()
            .nunique()
        )

    stale_df = (
        source_problem_df.groupby(["source", "symbol"], dropna=False)
        .agg(
            stale_snapshots=("problem", "count"),
            first_stale_time=("event_time", "min"),
            latest_stale_time=("event_time", "max"),
        )
        .reset_index()
    )

    stale_df["recent_cycles_analyzed"] = recent_cycles_analyzed

    if recent_cycles_analyzed:
        stale_df["stale_snapshot_pct"] = (
            stale_df["stale_snapshots"] / recent_cycles_analyzed * 100
        )
    else:
        stale_df["stale_snapshot_pct"] = None

    return stale_df[columns].sort_values(
        ["stale_snapshot_pct", "stale_snapshots", "latest_stale_time"],
        ascending=[False, False, False],
    )


def load_collection_coverage_tables():
    history_df = cached_collection_coverage_history()
    coverage_df, problem_df = build_collection_coverage_tables(history_df)
    cycle_metrics = calculate_collection_cycle_metrics(
        coverage_df,
        expected_interval_seconds=COLLECTION_INTERVAL_SECONDS,
        cadence_warning_seconds=COLLECTION_CADENCE_WARNING_SECONDS,
    )
    repeated_problem_df = calculate_repeated_problem_symbols(problem_df)
    problem_summary_df = calculate_problem_summary(problem_df)
    stale_vnx_symbols_df = calculate_dashboard_stale_symbol_summary(
        problem_df,
        coverage_df,
        source="VNX",
    )

    return (
        coverage_df,
        problem_df,
        cycle_metrics,
        repeated_problem_df,
        problem_summary_df,
        stale_vnx_symbols_df,
    )


def calculate_latest_coverage_totals(coverage_df):
    if coverage_df.empty:
        return {
            "latest_event_time": None,
            "requested_total": 0,
            "returned_total": 0,
            "ok_total": 0,
            "missing_total": 0,
            "problem_total": 0,
        }

    latest_event_time = coverage_df["event_time"].max()
    latest_rows = coverage_df[coverage_df["event_time"] == latest_event_time]

    return {
        "latest_event_time": latest_event_time,
        "requested_total": latest_rows["requested_count"].sum(),
        "returned_total": latest_rows["returned_count"].sum(),
        "ok_total": latest_rows["ok_count"].sum(),
        "missing_total": latest_rows["missing_count"].sum(),
        "problem_total": latest_rows["problem_count"].sum(),
    }


def format_seconds_metric(value, decimals=0):
    if value is None or pd.isna(value):
        return "N/A"

    return f"{format_float(value, decimals)} sec"


def render_latest_coverage_summary():
    coverage_df, _, _, _, _, _ = load_collection_coverage_tables()
    coverage_totals = calculate_latest_coverage_totals(coverage_df)

    if coverage_df.empty:
        st.info("No recent collector snapshot coverage summaries are available yet.")
        return

    st.subheader("Latest Coverage Monitor")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Latest Coverage Time",
        format_timestamp(coverage_totals["latest_event_time"]),
    )
    col2.metric(
        "Fresh / Requested",
        (
            f"{format_number(coverage_totals['ok_total'])} / "
            f"{format_number(coverage_totals['requested_total'])}"
        ),
    )
    col3.metric(
        "Returned / Requested",
        (
            f"{format_number(coverage_totals['returned_total'])} / "
            f"{format_number(coverage_totals['requested_total'])}"
        ),
    )
    col4.metric(
        "Problem Snapshots",
        format_number(coverage_totals["problem_total"]),
    )


def render_pipeline_health(health_summary):
    freshness = health_summary.get("freshness", {})
    events_df = health_summary.get("events", pd.DataFrame())
    collector_event = get_latest_component_event(events_df, "collector")
    matcher_event = get_latest_component_event(events_df, "matcher")
    replica_event = get_latest_component_event(
        events_df,
        "laptop_matched_replica",
    )

    latest_matched_time = freshness.get("latest_matched_quote_time")
    latest_vnx_time = freshness.get("latest_vnx_quote_time")
    latest_delayed_time = freshness.get("latest_delayed_quote_time")
    freshness_status = calculate_freshness_status(
        latest_matched_time=latest_matched_time,
        latest_raw_time=latest_vnx_time,
        collection_interval_seconds=COLLECTION_INTERVAL_SECONDS,
        matcher_interval_seconds=MATCHER_INTERVAL_SECONDS,
    )

    status_message = (
        f"{freshness_status['label']}: {freshness_status['message']} "
        f"Matched age: {format_age(freshness_status['matched_age_seconds'])}. "
        f"VNX age: {format_age(freshness_status['raw_age_seconds'])}."
    )

    if freshness_status["level"] == "fresh":
        st.success(status_message)
    elif freshness_status["level"] == "delayed":
        st.warning(status_message)
    elif freshness_status["level"] == "stale":
        st.error(status_message)
    else:
        st.info(status_message)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Latest Matched Quote",
        format_timestamp(latest_matched_time),
    )
    col2.metric(
        "Latest VNX Quote",
        format_timestamp(latest_vnx_time),
    )
    col3.metric(
        "Matched Rows Today",
        format_number(freshness.get("matched_rows_today")),
    )
    col4.metric(
        "Source Rows Today",
        format_number(freshness.get("vnx_rows_today")),
    )

    col5, col6, col7, col8 = st.columns(4)

    col5.metric(
        "Latest Delayed Quote",
        format_timestamp(latest_delayed_time),
    )
    col6.metric(
        "Latest Collector Run",
        format_timestamp(
            collector_event["event_time"] if collector_event else None
        ),
    )
    col7.metric(
        "Latest Matcher Run",
        format_timestamp(
            matcher_event["event_time"] if matcher_event else None
        ),
    )
    col8.metric(
        "Latest Cloud Sync",
        format_timestamp(
            replica_event["event_time"] if replica_event else None
        ),
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Pipeline Health")
    st.sidebar.write(f"Freshness: {freshness_status['label']}")
    st.sidebar.write(
        f"Matched age: {format_age(freshness_status['matched_age_seconds'])}"
    )
    st.sidebar.write(
        f"VNX age: {format_age(freshness_status['raw_age_seconds'])}"
    )

    if replica_event:
        st.sidebar.write(f"Laptop sync: {replica_event['status']}")

    if collector_event:
        st.sidebar.write(f"Collector: {collector_event['status']}")

    if matcher_event:
        st.sidebar.write(f"Matcher: {matcher_event['status']}")

    with st.expander("Pipeline Health Details"):
        if events_df.empty:
            st.caption("No pipeline health events recorded yet.")
            return

        display_events = events_df.copy()
        display_events["event_time"] = display_events["event_time"].apply(
            format_timestamp
        )
        display_events["details"] = display_events["details"].astype(str)

        st.dataframe(
            display_events,
            use_container_width=True,
            height=180,
        )


def render_metric_row(overall_metrics):
    """
    Display KPI cards.
    """

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Matched Observations",
        format_number(overall_metrics["total_observations"]),
    )

    col2.metric(
        "Symbols Analyzed",
        format_number(overall_metrics["symbols_analyzed"]),
    )

    col3.metric(
        "P50 Abs Diff",
        format_cents(overall_metrics["median_price_error_cents"]),
    )

    col4.metric(
        "P90 Abs Diff",
        format_cents(overall_metrics["p90_price_error_cents"]),
    )

    col5, col6, col7, col8 = st.columns(4)

    col5.metric(
        "P95 Abs Diff",
        format_cents(overall_metrics["p95_price_error_cents"]),
    )

    col6.metric(
        "P99 Abs Diff",
        format_cents(overall_metrics["p99_price_error_cents"]),
    )

    col7.metric(
        "Median Normalized Diff",
        format_bps(overall_metrics["median_price_error_bps"]),
    )

    col8.metric(
        "P95 Normalized Diff",
        format_bps(overall_metrics["p95_price_error_bps"]),
    )

    col9, col10, col11, col12 = st.columns(4)

    col9.metric(
        "Avg Abs Diff",
        format_cents(overall_metrics["avg_price_error_cents"]),
    )

    col10.metric(
        "Avg Directional Bias",
        format_signed_cents(overall_metrics["avg_directional_error_cents"]),
    )

    col11.metric(
        "Avg Normalized Bias",
        format_signed_bps(overall_metrics["avg_directional_error_bps"]),
    )

    col12.metric(
        "Avg Time Gap",
        f"{format_float(overall_metrics['avg_time_gap_seconds'], 2)} sec",
    )


def get_date_filters(min_date, max_date):
    """
    Build date range filters.
    """

    st.sidebar.subheader("Date Filter")

    period_option = st.sidebar.radio(
        "Select period",
        ["Latest Day", "Last 7 Days", "Last 30 Days", "Custom Range"],
        index=1,
    )

    if period_option == "Latest Day":
        start_date = max_date
        end_date = max_date

    elif period_option == "Last 7 Days":
        start_date = max_date - timedelta(days=6)
        end_date = max_date

    elif period_option == "Last 30 Days":
        start_date = max_date - timedelta(days=29)
        end_date = max_date

    else:
        selected_range = st.sidebar.date_input(
            "Custom date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start_date, end_date = selected_range
        else:
            start_date = min_date
            end_date = max_date

    if start_date < min_date:
        start_date = min_date

    if end_date > max_date:
        end_date = max_date

    return start_date, end_date, period_option


def get_sidebar_filters(symbols_df, sectors, min_date, max_date):
    """
    Build sidebar filters and return selected values.
    """

    st.sidebar.title("Dashboard Filters")

    start_date, end_date, period_option = get_date_filters(min_date, max_date)

    st.sidebar.subheader("Universe Filter")

    sector_options = ["All Sectors"] + sectors

    selected_sector_option = st.sidebar.multiselect(
        "Sector",
        options=sector_options,
        default=["All Sectors"],
    )

    if "All Sectors" in selected_sector_option or not selected_sector_option:
        selected_sectors = None
    else:
        selected_sectors = selected_sector_option

    symbol_options = symbols_df["symbol"].tolist()

    selected_symbol_option = st.sidebar.multiselect(
        "Ticker",
        options=symbol_options,
        default=[],
        help="Leave empty to include all tickers.",
    )

    selected_symbols = selected_symbol_option if selected_symbol_option else None

    st.sidebar.subheader("Matching Filter")

    timestamp_window_option = st.sidebar.selectbox(
        "Timestamp window",
        options=[1, 5, 15, 30, 60],
        index=4,
        help=(
            "Select the maximum allowed timestamp gap between VNX and delayed/reference quotes. "
            "Wide-gap matches are excluded because they mix market price movement with quote error."
        ),
    )

    max_time_gap_seconds = timestamp_window_option
    valid_only = True

    observation_interval_options = {
        "1 minute": 1,
        "5 minutes": 5,
        "15 minutes": 15,
        "1 hour": 60,
    }

    observation_interval_label = st.sidebar.selectbox(
        "Observation count interval",
        options=list(observation_interval_options.keys()),
        index=1,
    )

    st.sidebar.subheader("Table Display")

    top_n = st.sidebar.slider(
        "Top N symbols for charts",
        min_value=5,
        max_value=50,
        value=20,
        step=5,
    )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "period_option": period_option,
        "selected_symbols": selected_symbols,
        "selected_sectors": selected_sectors,
        "max_time_gap_seconds": max_time_gap_seconds,
        "top_n": top_n,
        "valid_only": valid_only,
        "timestamp_window_option": timestamp_window_option,
        "observation_interval_label": observation_interval_label,
        "observation_interval_minutes": observation_interval_options[
            observation_interval_label
        ],
    }


def render_executive_overview(df, symbol_stats, threshold_df, filters):
    st.header("Executive Summary")

    render_latest_coverage_summary()

    st.markdown("---")

    st.subheader("Accuracy Monitor")

    overall_metrics = calculate_overall_metrics(df)

    render_metric_row(overall_metrics)

    st.markdown("---")

    st.subheader("Cents Difference Analysis")

    st.plotly_chart(
        create_error_threshold_chart(threshold_df),
        use_container_width=True,
    )

    st.subheader("Observation Counts")

    observation_interval_df = calculate_observation_interval_summary(
        df,
        filters["observation_interval_minutes"],
    )

    col_interval, col_symbol = st.columns(2)

    with col_interval:
        st.plotly_chart(
            create_observation_interval_chart(
                observation_interval_df,
                filters["observation_interval_label"],
            ),
            use_container_width=True,
        )

    with col_symbol:
        st.plotly_chart(
            create_observation_count_chart(symbol_stats, filters["top_n"]),
            use_container_width=True,
        )

    display_interval_df = prepare_display_table(observation_interval_df)

    for column in ["interval_start", "interval_end"]:
        if column in display_interval_df.columns:
            display_interval_df[column] = pd.to_datetime(
                display_interval_df[column],
                errors="coerce",
            ).dt.strftime("%Y-%m-%d %H:%M:%S")

    st.dataframe(
        display_interval_df,
        use_container_width=True,
        height=260,
    )

    st.subheader("Price Band Normalization")

    price_band_df = calculate_price_band_summary(df)

    col_price_chart, col_price_table = st.columns(2)

    with col_price_chart:
        st.plotly_chart(
            create_price_band_chart(price_band_df),
            use_container_width=True,
        )

    with col_price_table:
        st.dataframe(
            prepare_display_table(price_band_df),
            use_container_width=True,
            height=450,
        )

    st.subheader("Symbol Difference Ranking")

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            create_worst_symbols_chart(symbol_stats, filters["top_n"]),
            use_container_width=True,
        )

    with col2:
        st.plotly_chart(
            create_best_symbols_chart(symbol_stats, filters["top_n"]),
            use_container_width=True,
        )

    st.plotly_chart(
        create_directional_error_by_symbol_chart(symbol_stats, filters["top_n"]),
        use_container_width=True,
    )


def render_symbol_level_accuracy(symbol_stats, filters):
    st.header("Accuracy Monitor")

    st.caption(
        "Symbol-level VNX quote accuracy using only valid timestamp-windowed matches."
    )

    display_df = prepare_display_table(symbol_stats)

    st.dataframe(
        display_df,
        use_container_width=True,
        height=600,
    )

    export_df = clean_export_dataframe(symbol_stats)

    st.download_button(
        label="Download Symbol-Level Stats CSV",
        data=dataframe_to_csv_bytes(export_df),
        file_name=build_export_filename(
            "symbol_level_accuracy",
            filters["start_date"],
            filters["end_date"],
        ),
        mime="text/csv",
    )


def render_ticker_deep_dive(df, symbols_df, filters):
    st.header("Ticker Deep Dive")

    symbol_options = sorted(df["symbol"].dropna().unique().tolist())

    if not symbol_options:
        st.warning("No symbols available for the selected filters.")
        return

    default_index = 0

    selected_ticker = st.selectbox(
        "Select ticker for detailed analysis",
        options=symbol_options,
        index=default_index,
    )

    ticker_metrics, ticker_df = calculate_ticker_metrics(df, selected_ticker)

    company_row = symbols_df[symbols_df["symbol"] == selected_ticker]

    if not company_row.empty:
        company_name = company_row.iloc[0]["company_name"]
        sector = company_row.iloc[0]["sector"]
        sub_industry = company_row.iloc[0]["sub_industry"]

        st.subheader(f"{selected_ticker} - {company_name}")
        st.caption(f"Sector: {sector} | Sub-industry: {sub_industry}")
    else:
        st.subheader(selected_ticker)

    render_metric_row(ticker_metrics)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            create_price_comparison_chart(ticker_df, selected_ticker),
            use_container_width=True,
        )

    with col2:
        st.plotly_chart(
            create_absolute_error_over_time_chart(ticker_df, selected_ticker),
            use_container_width=True,
        )

    col3, col4 = st.columns(2)

    with col3:
        st.plotly_chart(
            create_directional_error_over_time_chart(ticker_df, selected_ticker),
            use_container_width=True,
        )

    with col4:
        st.plotly_chart(
            create_time_gap_over_time_chart(ticker_df, selected_ticker),
            use_container_width=True,
        )

    st.subheader("Matched Observations")

    st.dataframe(
        ticker_df.sort_values("vnx_time", ascending=False),
        use_container_width=True,
        height=500,
    )

    export_df = clean_export_dataframe(ticker_df)

    st.download_button(
        label=f"Download {selected_ticker} Matched Observations CSV",
        data=dataframe_to_csv_bytes(export_df),
        file_name=build_export_filename(
            "ticker_matched_observations",
            filters["start_date"],
            filters["end_date"],
            selected_ticker,
        ),
        mime="text/csv",
    )


def render_timestamp_window_analysis(filters):
    st.header("Timestamp Windows")

    window_df = cached_window_summary(
        filters["start_date"],
        filters["end_date"],
        filters["selected_symbols"],
        filters["selected_sectors"],
    )

    if window_df.empty:
        st.warning("No timestamp-window data available.")
        return

    st.caption(
        "Use this to validate the matching window. The dashboard accuracy views "
        "use only rows inside the selected timestamp window."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            create_timestamp_window_chart(window_df),
            use_container_width=True,
        )

    with col2:
        st.plotly_chart(
            create_window_observation_chart(window_df),
            use_container_width=True,
        )

    display_df = window_df.copy()

    signed_cents_columns = [
        "avg_directional_error_cents",
    ]

    cents_columns = [
        "avg_price_error_cents",
        "median_price_error_cents",
        "max_price_error_cents",
    ]

    for column in signed_cents_columns:
        display_df[column] = display_df[column].apply(format_signed_cents)

    for column in cents_columns:
        display_df[column] = display_df[column].apply(format_cents)

    percent_columns = [
        "avg_price_error_pct",
        "median_price_error_pct",
        "max_price_error_pct",
        "avg_directional_error_pct",
    ]

    for column in percent_columns:
        display_df[column] = display_df[column].apply(format_percent)

    display_df["avg_time_gap_seconds"] = display_df["avg_time_gap_seconds"].apply(
        lambda value: format_float(value, 2)
    )

    st.dataframe(display_df, use_container_width=True)

    st.download_button(
        label="Download Timestamp Window Summary CSV",
        data=dataframe_to_csv_bytes(clean_export_dataframe(window_df)),
        file_name=build_export_filename(
            "timestamp_window_summary",
            filters["start_date"],
            filters["end_date"],
        ),
        mime="text/csv",
    )


def render_collection_snapshot_coverage():
    st.subheader("Snapshot Collection Coverage")

    (
        coverage_df,
        problem_df,
        cycle_metrics,
        repeated_problem_df,
        problem_summary_df,
        stale_vnx_symbols_df,
    ) = load_collection_coverage_tables()

    if coverage_df.empty:
        st.caption(
            "No collector snapshot coverage summaries found yet. "
            "Run the market pipeline after updating the database schema."
        )
        return

    coverage_totals = calculate_latest_coverage_totals(coverage_df)
    latest_event_time = coverage_totals["latest_event_time"]
    latest_rows = coverage_df[coverage_df["event_time"] == latest_event_time]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Latest Coverage Time", format_timestamp(latest_event_time))
    col2.metric(
        "Requested Snapshots",
        format_number(coverage_totals["requested_total"]),
    )
    col3.metric(
        "Returned Snapshots",
        format_number(coverage_totals["returned_total"]),
    )
    col4.metric(
        "Fresh Snapshots",
        format_number(coverage_totals["ok_total"]),
    )

    col5, col6, col7, col8, col9 = st.columns(5)

    col5.metric(
        "Problem Snapshots",
        format_number(coverage_totals["problem_total"]),
    )
    col6.metric(
        "Actual Cycles",
        format_number(cycle_metrics["actual_cycles"]),
    )
    col7.metric(
        "Avg Cycle Gap",
        format_seconds_metric(cycle_metrics["avg_cycle_gap_seconds"]),
    )
    col8.metric(
        "Max Cycle Gap",
        format_seconds_metric(cycle_metrics["max_cycle_gap_seconds"]),
    )
    col9.metric(
        f"Late Gaps > {format_number(cycle_metrics['cadence_warning_seconds'])} sec",
        format_number(cycle_metrics["late_gap_count"]),
    )

    if coverage_totals["problem_total"]:
        st.warning(
            f"Latest collector cycle has {format_number(coverage_totals['problem_total'])} "
            "snapshot coverage problems."
        )
    else:
        st.success("Latest collector cycle returned all requested VNX and delayed snapshots.")

    st.subheader("Latest Feed-Level Coverage")
    latest_display_df = latest_rows.copy()

    for column in ["event_time", "cycle_started_at", "source_timestamp_min", "source_timestamp_max"]:
        if column in latest_display_df.columns:
            latest_display_df[column] = pd.to_datetime(
                latest_display_df[column],
                errors="coerce",
            ).apply(format_timestamp)

    st.dataframe(
        latest_display_df,
        use_container_width=True,
        height=150,
    )

    st.subheader("Recent Polling Cycle History")

    display_coverage_df = coverage_df.copy()

    for column in ["event_time", "cycle_started_at", "source_timestamp_min", "source_timestamp_max"]:
        if column in display_coverage_df.columns:
            display_coverage_df[column] = pd.to_datetime(
                display_coverage_df[column],
                errors="coerce",
            ).apply(format_timestamp)

    st.dataframe(
        display_coverage_df,
        use_container_width=True,
        height=300,
    )

    st.download_button(
        label="Download Snapshot Coverage History CSV",
        data=dataframe_to_csv_bytes(clean_export_dataframe(coverage_df)),
        file_name="snapshot_collection_coverage.csv",
        mime="text/csv",
    )

    if problem_df.empty:
        st.caption("No missing or malformed symbols found in recent collector cycles.")
        return

    st.subheader("Problem Reason Summary")

    display_problem_summary_df = problem_summary_df.copy()

    if "latest_problem_time" in display_problem_summary_df.columns:
        display_problem_summary_df["latest_problem_time"] = pd.to_datetime(
            display_problem_summary_df["latest_problem_time"],
            errors="coerce",
        ).apply(format_timestamp)

    st.dataframe(
        display_problem_summary_df,
        use_container_width=True,
        height=220,
    )

    if not stale_vnx_symbols_df.empty:
        st.subheader("Most Stale VNX Symbols")

        display_stale_vnx_df = stale_vnx_symbols_df.copy()
        symbols_df = cached_symbols()

        if not symbols_df.empty:
            display_stale_vnx_df = display_stale_vnx_df.merge(
                symbols_df,
                on="symbol",
                how="left",
            )

        for column in ["first_stale_time", "latest_stale_time"]:
            if column in display_stale_vnx_df.columns:
                display_stale_vnx_df[column] = pd.to_datetime(
                    display_stale_vnx_df[column],
                    errors="coerce",
                ).apply(format_timestamp)

        if "stale_snapshot_pct" in display_stale_vnx_df.columns:
            display_stale_vnx_df["stale_snapshot_pct"] = (
                display_stale_vnx_df["stale_snapshot_pct"]
                .apply(
                    lambda value: (
                        f"{format_float(value, 2)}%"
                        if value is not None and not pd.isna(value)
                        else "N/A"
                    )
                )
            )

        stale_vnx_columns = [
            "symbol",
            "company_name",
            "sector",
            "stale_snapshots",
            "recent_cycles_analyzed",
            "stale_snapshot_pct",
            "latest_stale_time",
            "first_stale_time",
        ]

        st.dataframe(
            display_stale_vnx_df[
                [
                    column
                    for column in stale_vnx_columns
                    if column in display_stale_vnx_df.columns
                ]
            ].head(100),
            use_container_width=True,
            height=300,
        )

        st.download_button(
            label="Download Stale VNX Symbols CSV",
            data=dataframe_to_csv_bytes(
                clean_export_dataframe(stale_vnx_symbols_df)
            ),
            file_name="snapshot_stale_vnx_symbols.csv",
            mime="text/csv",
        )

    latest_problem_df = problem_df[problem_df["event_time"] == latest_event_time]

    if not latest_problem_df.empty:
        st.subheader("Latest Cycle Problem Symbols")

        display_latest_problem_df = latest_problem_df.copy()

        for column in ["event_time", "cycle_started_at"]:
            if column in display_latest_problem_df.columns:
                display_latest_problem_df[column] = pd.to_datetime(
                    display_latest_problem_df[column],
                    errors="coerce",
                ).apply(format_timestamp)

        st.dataframe(
            display_latest_problem_df.sort_values(["source", "problem", "symbol"]),
            use_container_width=True,
            height=300,
        )

    st.subheader("Repeated Problem Symbols")

    display_repeated_df = repeated_problem_df.copy()

    if "latest_problem_time" in display_repeated_df.columns:
        display_repeated_df["latest_problem_time"] = pd.to_datetime(
            display_repeated_df["latest_problem_time"],
            errors="coerce",
        ).apply(format_timestamp)

    st.dataframe(
        display_repeated_df.head(100),
        use_container_width=True,
        height=300,
    )

    st.subheader("Recent Problem Symbols")

    display_problem_df = problem_df.copy()

    for column in ["event_time", "cycle_started_at"]:
        if column in display_problem_df.columns:
            display_problem_df[column] = pd.to_datetime(
                display_problem_df[column],
                errors="coerce",
            ).apply(format_timestamp)

    st.dataframe(
        display_problem_df.sort_values("event_time", ascending=False).head(500),
        use_container_width=True,
        height=300,
    )

    st.download_button(
        label="Download Problem Symbols CSV",
        data=dataframe_to_csv_bytes(clean_export_dataframe(problem_df)),
        file_name="snapshot_collection_problem_symbols.csv",
        mime="text/csv",
    )


def render_data_coverage():
    st.header("Coverage Monitor")

    data_coverage_df = cached_data_coverage()
    coverage_metrics = calculate_data_coverage_metrics(data_coverage_df)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Symbols Loaded", format_number(coverage_metrics["symbols_loaded"]))
    col2.metric(
        "Symbols with Matched Data",
        format_number(coverage_metrics["symbols_with_matched"]),
    )
    col3.metric(
        "Matched Rows",
        format_number(coverage_metrics["total_matched_rows"]),
    )
    col4.metric(
        "Latest Matched Quote",
        format_timestamp(coverage_metrics["latest_matched_time"]),
    )

    col5, col6, col7 = st.columns(3)

    col5.metric("VNX Raw Rows", format_number(coverage_metrics["total_vnx_rows"]))
    col6.metric(
        "Delayed Raw Rows",
        format_number(coverage_metrics["total_delayed_rows"]),
    )
    col7.metric(
        "Symbols with Raw Both",
        format_number(coverage_metrics["symbols_with_both"]),
    )

    st.markdown("---")

    render_collection_snapshot_coverage()

    st.markdown("---")

    st.subheader("Matched/Raw Storage Coverage")

    st.dataframe(data_coverage_df, use_container_width=True, height=600)

    st.download_button(
        label="Download Data Coverage CSV",
        data=dataframe_to_csv_bytes(clean_export_dataframe(data_coverage_df)),
        file_name="data_coverage.csv",
        mime="text/csv",
    )


def render_downloads(df, symbol_stats, threshold_df, filters):
    st.header("Downloads")

    st.write("Download the currently filtered datasets and summary tables.")
    (
        collection_coverage_df,
        problem_symbols_df,
        _,
        repeated_problem_df,
        problem_summary_df,
        stale_vnx_symbols_df,
    ) = load_collection_coverage_tables()

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="Download Filtered Matched Observations",
            data=dataframe_to_csv_bytes(clean_export_dataframe(df)),
            file_name=build_export_filename(
                "filtered_matched_observations",
                filters["start_date"],
                filters["end_date"],
            ),
            mime="text/csv",
        )

        st.download_button(
            label="Download Symbol-Level Accuracy Stats",
            data=dataframe_to_csv_bytes(clean_export_dataframe(symbol_stats)),
            file_name=build_export_filename(
                "symbol_level_accuracy",
                filters["start_date"],
                filters["end_date"],
            ),
            mime="text/csv",
        )

    with col2:
        st.download_button(
            label="Download Cents Threshold Summary",
            data=dataframe_to_csv_bytes(clean_export_dataframe(threshold_df)),
            file_name=build_export_filename(
                "cents_threshold_summary",
                filters["start_date"],
                filters["end_date"],
            ),
            mime="text/csv",
        )

        observation_interval_df = calculate_observation_interval_summary(
            df,
            filters["observation_interval_minutes"],
        )
        price_band_df = calculate_price_band_summary(df)

        st.download_button(
            label="Download Observation Counts",
            data=dataframe_to_csv_bytes(
                clean_export_dataframe(observation_interval_df)
            ),
            file_name=build_export_filename(
                "observation_counts",
                filters["start_date"],
                filters["end_date"],
            ),
            mime="text/csv",
        )

        st.download_button(
            label="Download Price Band Summary",
            data=dataframe_to_csv_bytes(clean_export_dataframe(price_band_df)),
            file_name=build_export_filename(
                "price_band_summary",
                filters["start_date"],
                filters["end_date"],
            ),
            mime="text/csv",
        )

        data_coverage_df = cached_data_coverage()

        st.download_button(
            label="Download Data Coverage",
            data=dataframe_to_csv_bytes(clean_export_dataframe(data_coverage_df)),
            file_name="data_coverage.csv",
            mime="text/csv",
        )

        st.download_button(
            label="Download Snapshot Coverage History",
            data=dataframe_to_csv_bytes(
                clean_export_dataframe(collection_coverage_df)
            ),
            file_name="snapshot_collection_coverage.csv",
            mime="text/csv",
        )

        st.download_button(
            label="Download Problem Symbols",
            data=dataframe_to_csv_bytes(clean_export_dataframe(problem_symbols_df)),
            file_name="snapshot_collection_problem_symbols.csv",
            mime="text/csv",
        )

        st.download_button(
            label="Download Problem Reason Summary",
            data=dataframe_to_csv_bytes(clean_export_dataframe(problem_summary_df)),
            file_name="snapshot_collection_problem_reason_summary.csv",
            mime="text/csv",
        )

        st.download_button(
            label="Download Stale VNX Symbols",
            data=dataframe_to_csv_bytes(clean_export_dataframe(stale_vnx_symbols_df)),
            file_name="snapshot_stale_vnx_symbols.csv",
            mime="text/csv",
        )

        st.download_button(
            label="Download Repeated Problem Symbols",
            data=dataframe_to_csv_bytes(clean_export_dataframe(repeated_problem_df)),
            file_name="snapshot_repeated_problem_symbols.csv",
            mime="text/csv",
        )


def main():
    apply_page_config()
    apply_custom_styles()

    require_dashboard_login()

    render_header()

    health_summary = cached_pipeline_health()
    render_pipeline_health(health_summary)

    min_date, max_date = cached_date_range()

    if min_date is None or max_date is None:
        st.error("No matched quote analysis data found in PostgreSQL.")
        return

    symbols_df = cached_symbols()
    sectors = cached_sectors()

    filters = get_sidebar_filters(symbols_df, sectors, min_date, max_date)

    st.sidebar.markdown("---")
    st.sidebar.write("Available data range:")
    st.sidebar.write(f"{min_date} to {max_date}")

    df = cached_matched_data(
        filters["start_date"],
        filters["end_date"],
        filters["selected_symbols"],
        filters["selected_sectors"],
        filters["max_time_gap_seconds"],
        filters["valid_only"],
    )

    if df.empty:
        st.warning("No matched data found for the selected filters.")
        render_methodology_note()
        return

    symbol_stats = calculate_symbol_metrics(df)
    threshold_df = calculate_error_threshold_summary(df)

    window_text = (
        "valid matches with timestamp window "
        f"<= {filters['max_time_gap_seconds']} seconds"
    )

    st.info(
        f"Showing data from {filters['start_date']} to {filters['end_date']} "
        f"with {window_text}."
    )

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "Executive Summary",
            "Coverage Monitor",
            "Accuracy Monitor",
            "Ticker Deep Dive",
            "Timestamp Windows",
            "Downloads",
        ]
    )

    with tab1:
        render_executive_overview(df, symbol_stats, threshold_df, filters)

    with tab2:
        render_data_coverage()

    with tab3:
        render_symbol_level_accuracy(symbol_stats, filters)

    with tab4:
        render_ticker_deep_dive(df, symbols_df, filters)

    with tab5:
        render_timestamp_window_analysis(filters)

    with tab6:
        render_downloads(df, symbol_stats, threshold_df, filters)

    render_methodology_note()


if __name__ == "__main__":
    main()
