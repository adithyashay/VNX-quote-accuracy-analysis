import pandas as pd


def dataframe_to_csv_bytes(df):
    """
    Convert a DataFrame to CSV bytes for Streamlit download buttons.
    """

    if df is None or df.empty:
        return "".encode("utf-8")

    return df.to_csv(index=False).encode("utf-8")


def clean_export_dataframe(df):
    """
    Prepare a DataFrame for export.

    This keeps numeric values as real numbers, unlike display tables where
    we may format values as strings with percent signs.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    export_df = df.copy()

    datetime_columns = [
        "vnx_time",
        "delayed_time",
        "earliest_vnx_time",
        "latest_vnx_time",
        "earliest_delayed_time",
        "latest_delayed_time",
    ]

    for column in datetime_columns:
        if column in export_df.columns:
            export_df[column] = pd.to_datetime(
                export_df[column],
                errors="coerce"
            ).astype(str)

    return export_df


def build_export_filename(prefix, start_date=None, end_date=None, ticker=None):
    """
    Build clean export file names.
    """

    parts = [prefix]

    if ticker:
        parts.append(str(ticker))

    if start_date and end_date:
        parts.append(f"{start_date}_to_{end_date}")

    filename = "_".join(parts)
    filename = filename.replace(" ", "_").replace("/", "-")

    return f"{filename}.csv"