import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def convert_timestamp(timestamp_ms):
    return datetime.fromtimestamp(timestamp_ms / 1000)


def build_symbol_path(symbols):
    """
    Convert a list of symbols into API path format.

    Example:
    ["AAPL", "MSFT", "TSLA"] -> "AAPL,MSFT,TSLA"
    """

    return ",".join(symbols)


def get_vnx_quotes_batch(symbols):
    """
    Get VNX realtime quotes for multiple symbols in one API call.
    """

    token = os.getenv("VIANEXUS_API_TOKEN")

    symbol_path = build_symbol_path(symbols)

    url = f"https://api.blueskyapi.com/v1/data/EDGE/VNX_QUOTE/{symbol_path}"

    params = {
        "token": token
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    quotes = []

    for quote in data:
        quotes.append({
            "symbol": quote["vnxSymbol"],
            "vnx_price": quote["vnxPrice"],
            "bid_price": quote["vnxBidPrice"],
            "ask_price": quote["vnxAskPrice"],
            "last_sale_price": quote["vnxLastSalePrice"],
            "timestamp_raw": quote["vnxTimestamp"],
            "timestamp_readable": convert_timestamp(quote["vnxTimestamp"]),
            "price_type": quote["vnxPriceType"]
        })

    return quotes


def get_delayed_quotes_batch(symbols):
    """
    Get delayed reference quotes for multiple symbols in one API call.
    """

    token = os.getenv("VIANEXUS_API_TOKEN")

    symbol_path = build_symbol_path(symbols)

    url = f"https://api.blueskyapi.com/v1/data/CORE/DELAYED_QUOTE/{symbol_path}"

    params = {
        "token": token
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    quotes = []

    for quote in data:
        quotes.append({
            "symbol": quote["symbol"],
            "delayed_price": quote["delayedPrice"],
            "high": quote["high"],
            "low": quote["low"],
            "delayed_size": quote["delayedSize"],
            "delayed_time_raw": quote["delayedPriceTime"],
            "delayed_time_readable": convert_timestamp(quote["delayedPriceTime"]),
            "total_volume": quote["totalVolume"],
            "processed_time_raw": quote["processedTime"],
            "processed_time_readable": convert_timestamp(quote["processedTime"])
        })

    return quotes
