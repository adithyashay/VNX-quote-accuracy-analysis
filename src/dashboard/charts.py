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
    Create absolute cents difference over time chart.
    """

    if df.empty:
        return empty_chart()

    chart_df = df.copy()
    chart_df = chart_df.sort_values("vnx_time")

    title = "Absolute Price Difference in Cents Over Time"
    if ticker:
        title = f"{ticker}: Absolute Price Difference in Cents Over Time"

    fig = px.line(
        chart_df,
        x="vnx_time",
        y="absolute_price_difference_cents",
        title=title,
        labels={
            "vnx_time": "VNX Time",
            "absolute_price_difference_cents": "Absolute Difference (cents)",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_directional_error_over_time_chart(df, ticker=None):
    """
    Create signed/directional cents difference over time chart.
    """

    if df.empty:
        return empty_chart()

    chart_df = df.copy()
    chart_df = chart_df.sort_values("vnx_time")

    title = "Directional Price Difference in Cents Over Time"
    if ticker:
        title = f"{ticker}: Directional Price Difference in Cents Over Time"

    fig = px.line(
        chart_df,
        x="vnx_time",
        y="price_difference_cents",
        title=title,
        labels={
            "vnx_time": "VNX Time",
            "price_difference_cents": "Directional Difference (cents)",
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
    Create bar chart for worst symbols by average absolute cents difference.
    """

    if symbol_stats.empty:
        return empty_chart()

    chart_df = symbol_stats.sort_values(
        "avg_price_error_cents",
        ascending=False,
    ).head(top_n)

    fig = px.bar(
        chart_df,
        x="symbol",
        y="avg_price_error_cents",
        hover_data=["company_name", "sector", "observations"],
        title=f"Worst {top_n} Symbols by Average Cents Difference",
        labels={
            "symbol": "Symbol",
            "avg_price_error_cents": "Average Difference (cents)",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_best_symbols_chart(symbol_stats, top_n=20):
    """
    Create bar chart for best symbols by average absolute cents difference.
    """

    if symbol_stats.empty:
        return empty_chart()

    chart_df = symbol_stats.sort_values(
        "avg_price_error_cents",
        ascending=True,
    ).head(top_n)

    fig = px.bar(
        chart_df,
        x="symbol",
        y="avg_price_error_cents",
        hover_data=["company_name", "sector", "observations"],
        title=f"Best {top_n} Symbols by Average Cents Difference",
        labels={
            "symbol": "Symbol",
            "avg_price_error_cents": "Average Difference (cents)",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_directional_error_by_symbol_chart(symbol_stats, top_n=30):
    """
    Create signed directional cents difference chart by symbol.
    """

    if symbol_stats.empty:
        return empty_chart()

    chart_df = symbol_stats.copy()

    chart_df["abs_directional_error"] = chart_df[
        "avg_directional_error_cents"
    ].abs()

    chart_df = chart_df.sort_values(
        "abs_directional_error",
        ascending=False,
    ).head(top_n)

    fig = px.bar(
        chart_df,
        x="symbol",
        y="avg_directional_error_cents",
        hover_data=["company_name", "sector", "observations"],
        title=f"Top {top_n} Symbols by Directional Cents Difference",
        labels={
            "symbol": "Symbol",
            "avg_directional_error_cents": "Average Directional Difference (cents)",
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
        ascending=False,
    ).head(top_n)

    fig = px.bar(
        chart_df,
        x="symbol",
        y="observations",
        hover_data=["company_name", "sector"],
        title=f"Top {top_n} Symbols by Observation Count",
        labels={
            "symbol": "Symbol",
            "observations": "Matched Observations",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_error_threshold_chart(threshold_df):
    """
    Create chart showing percent of observations within cents thresholds.
    """

    if threshold_df.empty:
        return empty_chart()

    chart_df = threshold_df.copy()
    chart_df["threshold_label"] = chart_df["threshold_cents"].apply(
        lambda value: f"<= {value:.0f} cents"
    )

    fig = px.bar(
        chart_df,
        x="threshold_label",
        y="percent_of_observations",
        text="percent_of_observations",
        title="Observations Within Cents Difference Thresholds",
        labels={
            "threshold_label": "Absolute Difference Threshold",
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
        y="avg_price_error_cents",
        markers=True,
        title="Average Cents Difference by Timestamp Window",
        labels={
            "timestamp_window_label": "Timestamp Window",
            "avg_price_error_cents": "Average Difference (cents)",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_observation_interval_chart(interval_df, interval_label=None):
    """
    Create chart for matched observations by collection-time interval.
    """

    if interval_df.empty:
        return empty_chart()

    chart_df = interval_df.copy()

    title = "Matched Observations by Time Interval"
    if interval_label:
        title = f"Matched Observations by {interval_label}"

    fig = px.bar(
        chart_df,
        x="interval_start",
        y="observations",
        hover_data=[
            "symbols_analyzed",
            "avg_price_error_cents",
            "max_price_error_cents",
            "avg_time_gap_seconds",
        ],
        title=title,
        labels={
            "interval_start": "Interval Start",
            "observations": "Matched Observations",
            "symbols_analyzed": "Symbols Observed",
            "avg_price_error_cents": "Avg Difference (cents)",
            "max_price_error_cents": "Max Difference (cents)",
            "avg_time_gap_seconds": "Avg Time Gap Seconds",
        },
    )

    fig.update_layout(height=450)

    return fig


def create_price_band_chart(price_band_df):
    """
    Create chart for price-band-normalized error review.
    """

    if price_band_df.empty:
        return empty_chart()

    chart_df = price_band_df.copy()

    fig = px.bar(
        chart_df,
        x="price_band",
        y="p95_price_error_cents",
        hover_data=[
            "observations",
            "symbols_analyzed",
            "median_price_error_cents",
            "p95_price_error_bps",
            "median_price_error_bps",
        ],
        title="P95 Cents Difference by Reference Price Band",
        labels={
            "price_band": "Reference Price Band",
            "p95_price_error_cents": "P95 Difference (cents)",
            "observations": "Matched Observations",
            "symbols_analyzed": "Symbols Observed",
            "median_price_error_cents": "Median Difference (cents)",
            "p95_price_error_bps": "P95 Difference (bps)",
            "median_price_error_bps": "Median Difference (bps)",
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
        title="Matched Observations by Timestamp Window",
        labels={
            "timestamp_window_label": "Timestamp Window",
            "observations": "Matched Observations",
        },
    )

    fig.update_layout(height=450)

    return fig
