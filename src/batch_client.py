import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.settings import get_vianexus_api_token

EASTERN_TIMEZONE = ZoneInfo("America/New_York")


def convert_timestamp(timestamp_ms):
    """
    Convert API millisecond timestamps into naive Eastern datetimes.

    PostgreSQL tables currently use TIMESTAMP rather than TIMESTAMPTZ, so the
    pipeline stores exchange-local Eastern time consistently and explicitly.
    """

    return (
        datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        .astimezone(EASTERN_TIMEZONE)
        .replace(tzinfo=None)
    )


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

    token = get_vianexus_api_token()

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

    token = get_vianexus_api_token()

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
