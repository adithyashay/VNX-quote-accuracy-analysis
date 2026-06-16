import requests
import pandas as pd
from pathlib import Path
from io import StringIO


OUTPUT_FILE = Path("config/sp500_symbols.csv")
SOURCE_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def download_sp500_symbols():
    """
    Download current S&P 500 constituents from Wikipedia and save them
    into config/sp500_symbols.csv.

    Uses a browser-like User-Agent to avoid 403 Forbidden errors.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    response = requests.get(SOURCE_URL, headers=headers, timeout=20)
    response.raise_for_status()

    tables = pd.read_html(StringIO(response.text))

    sp500_df = tables[0]

    sp500_df = sp500_df.rename(
        columns={
            "Symbol": "symbol",
            "Security": "company_name",
            "GICS Sector": "sector",
            "GICS Sub-Industry": "sub_industry"
        }
    )

    sp500_df = sp500_df[
        [
            "symbol",
            "company_name",
            "sector",
            "sub_industry"
        ]
    ]

    sp500_df["symbol"] = sp500_df["symbol"].astype(str).str.strip()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    sp500_df.to_csv(OUTPUT_FILE, index=False)

    print("Saved S&P 500 symbols to:", OUTPUT_FILE)
    print("Total symbols:", len(sp500_df))
    print()
    print(sp500_df.head())


if __name__ == "__main__":
    download_sp500_symbols()