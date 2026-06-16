import pandas as pd
from pathlib import Path


TEST_SYMBOLS = ["AAPL", "MSFT", "TSLA", "SSD"]

SP500_SAMPLE_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META",
    "GOOGL", "GOOG", "LLY", "AVGO", "JPM",
    "V", "UNH", "XOM", "MA", "COST",
    "HD", "PG", "NFLX", "BAC", "KO"
]


def load_sp500_symbols(file_path="config/sp500_symbols.csv"):
    """
    Load S&P 500 symbols from CSV.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            "S&P 500 symbol file not found. "
            "Run: python -m scripts.download_sp500_symbols"
        )

    df = pd.read_csv(path)

    symbols = (
        df["symbol"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    return symbols


SP500_SYMBOLS = load_sp500_symbols()

# Change this line to control what the pipeline collects.
# Options:
# ACTIVE_SYMBOLS = TEST_SYMBOLS
# ACTIVE_SYMBOLS = SP500_SAMPLE_SYMBOLS
# ACTIVE_SYMBOLS = SP500_SYMBOLS

ACTIVE_SYMBOLS = SP500_SYMBOLS