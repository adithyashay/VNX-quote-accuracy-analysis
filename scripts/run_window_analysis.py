from src.window_analysis import (
    calculate_overall_window_analysis,
    calculate_ticker_window_analysis
)


def format_percent(value):
    """
    Format numeric error values as percentages.
    Example: 0.0338 -> 0.0338%
    """

    if value is None:
        return "N/A"

    try:
        if value != value:  # catches NaN
            return "N/A"
    except TypeError:
        return "N/A"

    return f"{value:.4f}%"


def format_count(value):
    """
    Format count values.
    """

    if value is None:
        return "0"

    try:
        if value != value:  # catches NaN
            return "0"
    except TypeError:
        return "0"

    return str(int(value))


def prepare_overall_table(overall_df):
    """
    Convert technical column names into report-friendly names.
    """

    display_df = overall_df.copy()

    display_df["Window"] = display_df["window_seconds"].astype(str) + "s"
    display_df["Observations"] = display_df["match_count"].apply(format_count)
    display_df["New Observations"] = display_df["new_matches_added"].apply(
        format_count)
    display_df["Avg Price Error %"] = display_df["average_absolute_error"].apply(
        format_percent)
    display_df["Median Price Error %"] = display_df["median_absolute_error"].apply(
        format_percent)
    display_df["Min Price Error %"] = display_df["min_absolute_error"].apply(
        format_percent)
    display_df["Max Price Error %"] = display_df["max_absolute_error"].apply(
        format_percent)
    display_df["Error Std Dev %"] = display_df["standard_deviation_error"].apply(
        format_percent)
    display_df["Avg Directional Error %"] = display_df["average_signed_error"].apply(
        format_percent)

    return display_df[
    [
        "Window",
        "Observations",
        "Avg Price Error %",
        "Median Price Error %",
        "Max Price Error %",
        "Error Std Dev %",
        "Avg Directional Error %"
    ]
]


def prepare_ticker_table(ticker_df):
    """
    Convert ticker-level technical output into report-friendly names.
    """

    display_df = ticker_df.copy()

    display_df["Ticker"] = display_df["symbol"]
    display_df["Window"] = display_df["window_seconds"].astype(str) + "s"
    display_df["Observations"] = display_df["match_count"].apply(format_count)
    display_df["New Observations"] = display_df["new_matches_added"].apply(
        format_count)
    display_df["Avg Price Error %"] = display_df["average_absolute_error"].apply(
        format_percent)
    display_df["Median Price Error %"] = display_df["median_absolute_error"].apply(
        format_percent)
    display_df["Min Price Error %"] = display_df["min_absolute_error"].apply(
        format_percent)
    display_df["Max Price Error %"] = display_df["max_absolute_error"].apply(
        format_percent)
    display_df["Error Std Dev %"] = display_df["standard_deviation_error"].apply(
        format_percent)
    display_df["Avg Directional Error %"] = display_df["average_signed_error"].apply(
        format_percent)

    return display_df[
    [
        "Ticker",
        "Window",
        "Observations",
        "Avg Price Error %",
        "Median Price Error %",
        "Max Price Error %",
        "Avg Directional Error %"
    ]
]


def print_interpretation(overall_df):
    """
    Print a short interpretation of the timestamp-window analysis.
    """

    if overall_df.empty:
        print("No timestamp-window data available.")
        return

    smallest_window = overall_df.iloc[0]
    largest_window = overall_df.iloc[-1]

    print()
    print("Interpretation")
    print("--------------")
    print("Larger timestamp windows increase observations but may add timing noise.")

    window_30 = overall_df[overall_df["window_seconds"] == 30]
    window_60 = overall_df[overall_df["window_seconds"] == 60]

    if not window_30.empty and not window_60.empty:
        row_30 = window_30.iloc[0]
        row_60 = window_60.iloc[0]

        added_matches = int(row_60["match_count"] - row_30["match_count"])

        print(
            f"In this sample, 30s captures {int(row_30['match_count'])} observations, "
            f"while 60s captures {int(row_60['match_count'])} observations "
            f"({added_matches} more)."
       )

        print(
            "30s may be a reasonable candidate baseline, "
            "but this should be confirmed with more data."
       )


overall_window_analysis = calculate_overall_window_analysis()
ticker_window_analysis = calculate_ticker_window_analysis()

overall_display = prepare_overall_table(overall_window_analysis)
ticker_display = prepare_ticker_table(ticker_window_analysis)

print()
print("Overall Timestamp Window Analysis")
print("---------------------------------")
print(overall_display.to_string(index=False))

print()
print("Ticker-Level Timestamp Window Analysis")
print("--------------------------------------")
print(ticker_display.to_string(index=False))

print_interpretation(overall_window_analysis)