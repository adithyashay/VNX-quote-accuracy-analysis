import pandas as pd


def load_matched_data(file_path="data/processed/matched_quote_analysis.csv"):
    """
    Load the processed matched quote analysis CSV.
    """

    df = pd.read_csv(file_path)

    return df


def get_valid_matches(df):
    """
    Keep only timestamp-aligned matches.
    """

    valid_df = df[df["valid_match"] == True]

    return valid_df


def calculate_overall_statistics(file_path="data/processed/matched_quote_analysis.csv"):
    """
    Calculate overall accuracy statistics using only valid matches.
    """

    df = load_matched_data(file_path)

    valid_df = get_valid_matches(df)

    if valid_df.empty:
        return {
            "total_matches": len(df),
            "valid_matches": 0,
            "invalid_matches": len(df),
            "average_absolute_error": None,
            "median_absolute_error": None,
            "min_absolute_error": None,
            "max_absolute_error": None,
            "standard_deviation_error": None
        }

    return {
        "total_matches": len(df),
        "valid_matches": len(valid_df),
        "invalid_matches": len(df) - len(valid_df),
        "average_absolute_error": round(valid_df["absolute_percentage_error"].mean(), 4),
        "median_absolute_error": round(valid_df["absolute_percentage_error"].median(), 4),
        "min_absolute_error": round(valid_df["absolute_percentage_error"].min(), 4),
        "max_absolute_error": round(valid_df["absolute_percentage_error"].max(), 4),
        "standard_deviation_error": round(valid_df["absolute_percentage_error"].std(), 4)
    }


def calculate_error_by_ticker(file_path="data/processed/matched_quote_analysis.csv"):
    """
    Calculate average, median, max error by ticker using only valid matches.
    """

    df = load_matched_data(file_path)

    valid_df = get_valid_matches(df)

    if valid_df.empty:
        return pd.DataFrame()

    ticker_stats = valid_df.groupby("symbol")["absolute_percentage_error"].agg(
        valid_matches="count",
        average_error="mean",
        median_error="median",
        max_error="max",
        min_error="min"
    ).reset_index()

    ticker_stats["average_error"] = ticker_stats["average_error"].round(4)
    ticker_stats["median_error"] = ticker_stats["median_error"].round(4)
    ticker_stats["max_error"] = ticker_stats["max_error"].round(4)
    ticker_stats["min_error"] = ticker_stats["min_error"].round(4)

    return ticker_stats