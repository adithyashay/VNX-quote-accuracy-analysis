import pandas as pd


DEFAULT_WINDOWS = [1, 5, 15, 30, 60]


def load_matched_data(file_path="data/processed/matched_quote_analysis.csv"):
    """
    Load the processed matched quote analysis data.
    """

    df = pd.read_csv(file_path)

    return df


def calculate_error_stats(df):
    """
    Calculate error statistics for a filtered DataFrame.
    """

    if df.empty:
        return {
            "match_count": 0,
            "average_absolute_error": None,
            "median_absolute_error": None,
            "min_absolute_error": None,
            "max_absolute_error": None,
            "standard_deviation_error": None,
            "average_signed_error": None
        }

    return {
        "match_count": len(df),
        "average_absolute_error": round(df["absolute_percentage_error"].mean(), 4),
        "median_absolute_error": round(df["absolute_percentage_error"].median(), 4),
        "min_absolute_error": round(df["absolute_percentage_error"].min(), 4),
        "max_absolute_error": round(df["absolute_percentage_error"].max(), 4),
        "standard_deviation_error": round(df["absolute_percentage_error"].std(), 4),
        "average_signed_error": round(df["percentage_error"].mean(), 4)
    }


def add_new_matches_column(results):
    """
    Add a column showing how many new matches were gained
    compared to the previous timestamp window.
    """

    previous_count = 0

    for result in results:
        current_count = result["match_count"]
        result["new_matches_added"] = current_count - previous_count
        previous_count = current_count

    return results


def calculate_overall_window_analysis(
    file_path="data/processed/matched_quote_analysis.csv",
    windows=None
):
    """
    Calculate overall timestamp-window analysis.

    Each window means:
    include rows where time_gap_seconds <= window.
    """

    if windows is None:
        windows = DEFAULT_WINDOWS

    df = load_matched_data(file_path)

    results = []

    for window in windows:
        window_df = df[df["time_gap_seconds"] <= window]

        stats = calculate_error_stats(window_df)

        results.append({
            "window_seconds": window,
            **stats
        })

    results = add_new_matches_column(results)

    return pd.DataFrame(results)


def calculate_ticker_window_analysis(
    file_path="data/processed/matched_quote_analysis.csv",
    windows=None
):
    """
    Calculate timestamp-window analysis by ticker.
    """

    if windows is None:
        windows = DEFAULT_WINDOWS

    df = load_matched_data(file_path)

    results = []

    for symbol in sorted(df["symbol"].unique()):
        symbol_df = df[df["symbol"] == symbol]

        symbol_results = []

        for window in windows:
            window_df = symbol_df[symbol_df["time_gap_seconds"] <= window]

            stats = calculate_error_stats(window_df)

            symbol_results.append({
                "symbol": symbol,
                "window_seconds": window,
                **stats
            })

        symbol_results = add_new_matches_column(symbol_results)

        results.extend(symbol_results)

    return pd.DataFrame(results)