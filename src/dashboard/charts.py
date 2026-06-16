import pandas as pd
import plotly.express as px


def empty_chart(message="No data available for the selected filters."):
    """
    Return a simple placeholder chart when there is no data.
    """

    fig = px.scatter(
        x=[0],
        y=[0],
        text=[message],
        title=message,
    )

    fig.update_traces(textposition="middle center", marker=dict(size=0))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=300)

    return fig


def create_price_comparison_chart(df, ticker=None):
    """
    Create VNX vs delayed/reference price chart over time.
    Best used for one selected ticker.
    """

    if df.empty:
        return empty_chart()

    chart_df = df.copy()
    chart_df = chart_df.sort_values("vnx_time")

    title = "VNX Price vs Delayed Reference Price"
    if ticker:
        title = f"{ticker}: VNX Price vs Delayed Reference Price"

    long_df = chart_df.melt(
        id_vars=["vnx_time", "symbol"],
        value_vars=["vnx_price", "delayed_price"],
        var_name="price_type",
        value_name="price",
    )

    long_df["price_type"] = long_df["price_type"].replace(
        {
            "vnx_price": "VNX Price",
            "delayed_price": "Delayed Reference Price",
        }
    )

    fig = px.line(
        long_df,
        x="vnx_time",
        y="price",
        color="price_type",
        title=title,
        labels={
            "vnx_time": "VNX Time",
            "price": "Price",
            "price_type": "Price Type",
        },
    )

    fig.update_layout(
        height=450,
        legend_title_text="Series",
    )

    return fig


def create_absolute_error_over_time_chart(df, ticker=None):
    """
    Create absolute percentage error over time chart.
    """

    if df.empty:
        return empty_chart()

    chart_df = df.copy()
    chart_df = chart_df.sort_values("vnx_time")

    title = "Absolute Price Error % Over Time"
    if ticker:
        title = f"{ticker}: Absolute Price Error % Over Time"

    fig = px.line(
        chart_df,
        x="vnx_time",
        y="absolute_percentage_error",
        title=title,
        labels={
            "vnx_time": "VNX Time",
            "absolute_percentage_error": "Absolute Price Error %",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_directional_error_over_time_chart(df, ticker=None):
    """
    Create signed/directional percentage error over time chart.
    """

    if df.empty:
        return empty_chart()

    chart_df = df.copy()
    chart_df = chart_df.sort_values("vnx_time")

    title = "Directional Price Error % Over Time"
    if ticker:
        title = f"{ticker}: Directional Price Error % Over Time"

    fig = px.line(
        chart_df,
        x="vnx_time",
        y="percentage_error",
        title=title,
        labels={
            "vnx_time": "VNX Time",
            "percentage_error": "Directional Price Error %",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_time_gap_over_time_chart(df, ticker=None):
    """
    Create timestamp gap over time chart.
    """

    if df.empty:
        return empty_chart()

    chart_df = df.copy()
    chart_df = chart_df.sort_values("vnx_time")

    title = "Timestamp Gap Over Time"
    if ticker:
        title = f"{ticker}: Timestamp Gap Over Time"

    fig = px.line(
        chart_df,
        x="vnx_time",
        y="time_gap_seconds",
        title=title,
        labels={
            "vnx_time": "VNX Time",
            "time_gap_seconds": "Time Gap Seconds",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_worst_symbols_chart(symbol_stats, top_n=20):
    """
    Create bar chart for worst symbols by average absolute price error.
    """

    if symbol_stats.empty:
        return empty_chart()

    chart_df = symbol_stats.sort_values(
        "avg_price_error_pct",
        ascending=False
    ).head(top_n)

    fig = px.bar(
        chart_df,
        x="symbol",
        y="avg_price_error_pct",
        hover_data=["company_name", "sector", "observations"],
        title=f"Worst {top_n} Symbols by Average Price Error %",
        labels={
            "symbol": "Symbol",
            "avg_price_error_pct": "Average Price Error %",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_best_symbols_chart(symbol_stats, top_n=20):
    """
    Create bar chart for best symbols by average absolute price error.
    """

    if symbol_stats.empty:
        return empty_chart()

    chart_df = symbol_stats.sort_values(
        "avg_price_error_pct",
        ascending=True
    ).head(top_n)

    fig = px.bar(
        chart_df,
        x="symbol",
        y="avg_price_error_pct",
        hover_data=["company_name", "sector", "observations"],
        title=f"Best {top_n} Symbols by Average Price Error %",
        labels={
            "symbol": "Symbol",
            "avg_price_error_pct": "Average Price Error %",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_directional_error_by_symbol_chart(symbol_stats, top_n=30):
    """
    Create signed directional error chart by symbol.
    """

    if symbol_stats.empty:
        return empty_chart()

    chart_df = symbol_stats.copy()

    chart_df["abs_directional_error"] = chart_df[
        "avg_directional_error_pct"
    ].abs()

    chart_df = chart_df.sort_values(
        "abs_directional_error",
        ascending=False
    ).head(top_n)

    fig = px.bar(
        chart_df,
        x="symbol",
        y="avg_directional_error_pct",
        hover_data=["company_name", "sector", "observations"],
        title=f"Top {top_n} Symbols by Directional Error %",
        labels={
            "symbol": "Symbol",
            "avg_directional_error_pct": "Average Directional Error %",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_observation_count_chart(symbol_stats, top_n=30):
    """
    Create observation count chart by symbol.
    """

    if symbol_stats.empty:
        return empty_chart()

    chart_df = symbol_stats.sort_values(
        "observations",
        ascending=False
    ).head(top_n)

    fig = px.bar(
        chart_df,
        x="symbol",
        y="observations",
        hover_data=["company_name", "sector"],
        title=f"Top {top_n} Symbols by Observation Count",
        labels={
            "symbol": "Symbol",
            "observations": "Valid Observations",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_error_threshold_chart(threshold_df):
    """
    Create chart showing percent of observations within error thresholds.
    """

    if threshold_df.empty:
        return empty_chart()

    chart_df = threshold_df.copy()
    chart_df["threshold_label"] = chart_df["threshold"].apply(
        lambda value: f"≤ {value:.2f}%"
    )

    fig = px.bar(
        chart_df,
        x="threshold_label",
        y="percent_of_observations",
        text="percent_of_observations",
        title="Observations Within Error Thresholds",
        labels={
            "threshold_label": "Absolute Error Threshold",
            "percent_of_observations": "% of Observations",
        },
    )

    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig.update_layout(height=450)

    return fig


def create_timestamp_window_chart(window_df):
    """
    Create timestamp-window analysis chart.
    """

    if window_df.empty:
        return empty_chart()

    chart_df = window_df.copy()

    chart_df["timestamp_window_label"] = chart_df[
        "timestamp_window_seconds"
    ].apply(lambda value: f"{value}s")

    fig = px.line(
        chart_df,
        x="timestamp_window_label",
        y="avg_price_error_pct",
        markers=True,
        title="Average Price Error % by Timestamp Window",
        labels={
            "timestamp_window_label": "Timestamp Window",
            "avg_price_error_pct": "Average Price Error %",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_window_observation_chart(window_df):
    """
    Create chart for observation count by timestamp window.
    """

    if window_df.empty:
        return empty_chart()

    chart_df = window_df.copy()

    chart_df["timestamp_window_label"] = chart_df[
        "timestamp_window_seconds"
    ].apply(lambda value: f"{value}s")

    fig = px.bar(
        chart_df,
        x="timestamp_window_label",
        y="observations",
        title="Valid Observations by Timestamp Window",
        labels={
            "timestamp_window_label": "Timestamp Window",
            "observations": "Valid Observations",
        },
    )

    fig.update_layout(height=450)

    return fig