from datetime import timedelta

import pandas as pd
import streamlit as st

from src.settings import get_int_env
from src.dashboard.queries import (
    get_available_date_range,
    get_symbols,
    get_sectors,
    load_matched_data,
    load_pipeline_health_summary,
    load_raw_data_coverage,
    load_timestamp_window_summary,
)
from src.dashboard.metrics import (
    calculate_overall_metrics,
    calculate_symbol_metrics,
    calculate_ticker_metrics,
    calculate_error_threshold_summary,
    calculate_raw_coverage_metrics,
    prepare_display_table,
    format_percent,
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
def cached_raw_coverage():
    return load_raw_data_coverage()


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


def render_pipeline_health(health_summary):
    freshness = health_summary.get("freshness", {})
    events_df = health_summary.get("events", pd.DataFrame())

    latest_matched_time = freshness.get("latest_matched_quote_time")
    latest_vnx_time = freshness.get("latest_vnx_quote_time")
    freshness_status = calculate_freshness_status(
        latest_matched_time=latest_matched_time,
        latest_raw_time=latest_vnx_time,
        collection_interval_seconds=COLLECTION_INTERVAL_SECONDS,
        matcher_interval_seconds=MATCHER_INTERVAL_SECONDS,
    )

    status_message = (
        f"{freshness_status['label']}: {freshness_status['message']} "
        f"Matched age: {format_age(freshness_status['matched_age_seconds'])}. "
        f"Raw VNX age: {format_age(freshness_status['raw_age_seconds'])}."
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
        "VNX Rows Today",
        format_number(freshness.get("vnx_rows_today")),
    )

    collector_event = get_latest_component_event(events_df, "collector")
    matcher_event = get_latest_component_event(events_df, "matcher")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Pipeline Health")
    st.sidebar.write(f"Freshness: {freshness_status['label']}")
    st.sidebar.write(
        f"Matched age: {format_age(freshness_status['matched_age_seconds'])}"
    )
    st.sidebar.write(
        f"Raw VNX age: {format_age(freshness_status['raw_age_seconds'])}"
    )

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
    Render KPI cards.
    """

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Valid Observations",
        format_number(overall_metrics["total_observations"]),
    )

    col2.metric(
        "Symbols Analyzed",
        format_number(overall_metrics["symbols_analyzed"]),
    )

    col3.metric(
        "Avg Price Error",
        format_percent(overall_metrics["avg_price_error_pct"]),
    )

    col4.metric(
        "Median Price Error",
        format_percent(overall_metrics["median_price_error_pct"]),
    )

    col5, col6, col7, col8 = st.columns(4)

    col5.metric(
        "Max Price Error",
        format_percent(overall_metrics["max_price_error_pct"]),
    )

    col6.metric(
        "Directional Error",
        format_percent(overall_metrics["avg_directional_error_pct"]),
    )

    col7.metric(
        "Avg Time Gap",
        f"{format_float(overall_metrics['avg_time_gap_seconds'], 2)} sec",
    )

    col8.metric(
        "VNX Time Range",
        "Available",
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
        options=["All", 1, 5, 15, 30, 60],
        index=5,
        help=(
            "Select the maximum allowed timestamp gap between VNX and delayed/reference quotes. "
            "'All' includes every matched observation regardless of timestamp gap."
        ),
    )

    max_time_gap_seconds = (
        None
        if timestamp_window_option == "All"
        else timestamp_window_option
    )
    valid_only = timestamp_window_option != "All"

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
    }


def render_executive_overview(df, symbol_stats, threshold_df, filters):
    st.header("Executive Overview")

    overall_metrics = calculate_overall_metrics(df)

    render_metric_row(overall_metrics)

    st.markdown("---")

    st.subheader("Error and Accuracy Analysis")

    st.plotly_chart(
        create_error_threshold_chart(threshold_df),
        use_container_width=True,
    )

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
    st.header("Symbol-Level Accuracy")

    st.caption(
        "This table shows S&P 500 symbol-level VNX quote accuracy for the selected filters."
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
    st.header("Timestamp Window Analysis")

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
        "This section shows how observation count and accuracy change as the timestamp window changes."
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


def render_raw_data_coverage():
    st.header("Raw Data Coverage")

    raw_df = cached_raw_coverage()
    coverage_metrics = calculate_raw_coverage_metrics(raw_df)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Symbols Loaded", format_number(coverage_metrics["symbols_loaded"]))
    col2.metric("Symbols with VNX", format_number(coverage_metrics["symbols_with_vnx"]))
    col3.metric(
        "Symbols with Delayed",
        format_number(coverage_metrics["symbols_with_delayed"]),
    )
    col4.metric(
        "Symbols with Both",
        format_number(coverage_metrics["symbols_with_both"]),
    )

    col5, col6, col7 = st.columns(3)

    col5.metric("VNX Raw Rows", format_number(coverage_metrics["total_vnx_rows"]))
    col6.metric(
        "Delayed Raw Rows",
        format_number(coverage_metrics["total_delayed_rows"]),
    )
    col7.metric(
        "Matched Rows",
        format_number(coverage_metrics["total_matched_rows"]),
    )

    st.markdown("---")

    st.subheader("Symbol-Level Raw Coverage")

    st.dataframe(raw_df, use_container_width=True, height=600)

    st.download_button(
        label="Download Raw Data Coverage CSV",
        data=dataframe_to_csv_bytes(clean_export_dataframe(raw_df)),
        file_name="raw_data_coverage.csv",
        mime="text/csv",
    )


def render_downloads(df, symbol_stats, threshold_df, filters):
    st.header("Downloads")

    st.write("Download the currently filtered datasets and summary tables.")

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
            label="Download Error Threshold Summary",
            data=dataframe_to_csv_bytes(clean_export_dataframe(threshold_df)),
            file_name=build_export_filename(
                "error_threshold_summary",
                filters["start_date"],
                filters["end_date"],
            ),
            mime="text/csv",
        )

        raw_df = cached_raw_coverage()

        st.download_button(
            label="Download Raw Data Coverage",
            data=dataframe_to_csv_bytes(clean_export_dataframe(raw_df)),
            file_name="raw_data_coverage.csv",
            mime="text/csv",
        )


def main():
    apply_page_config()
    apply_custom_styles()
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
        "All timestamp gaps, including invalid/wide-gap matches"
        if filters["timestamp_window_option"] == "All"
        else (
            "valid matches with timestamp window "
            f"<= {filters['max_time_gap_seconds']} seconds"
        )
    )

    st.info(
        f"Showing data from {filters['start_date']} to {filters['end_date']} "
        f"with {window_text}."
    )

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "Executive Overview",
            "Symbol-Level Accuracy",
            "Ticker Deep Dive",
            "Timestamp Window Analysis",
            "Raw Data Coverage",
            "Downloads",
        ]
    )

    with tab1:
        render_executive_overview(df, symbol_stats, threshold_df, filters)

    with tab2:
        render_symbol_level_accuracy(symbol_stats, filters)

    with tab3:
        render_ticker_deep_dive(df, symbols_df, filters)

    with tab4:
        render_timestamp_window_analysis(filters)

    with tab5:
        render_raw_data_coverage()

    with tab6:
        render_downloads(df, symbol_stats, threshold_df, filters)

    render_methodology_note()


if __name__ == "__main__":
    main()
