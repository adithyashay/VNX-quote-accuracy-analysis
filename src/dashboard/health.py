from datetime import datetime

import pandas as pd

from src.market_hours import EASTERN_TIMEZONE, is_market_open_at


def normalize_timestamp(value):
    if value is None or pd.isna(value):
        return None

    timestamp = pd.Timestamp(value)

    if pd.isna(timestamp):
        return None

    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(EASTERN_TIMEZONE).tz_localize(None)

    return timestamp.to_pydatetime()


def normalize_current_time(value=None):
    if value is None:
        return datetime.now(EASTERN_TIMEZONE)

    if value.tzinfo is None:
        return value.replace(tzinfo=EASTERN_TIMEZONE)

    return value.astimezone(EASTERN_TIMEZONE)


def format_timestamp(value):
    timestamp = normalize_timestamp(value)

    if timestamp is None:
        return "N/A"

    return timestamp.strftime("%Y-%m-%d %H:%M:%S ET")


def format_age(seconds):
    if seconds is None:
        return "N/A"

    seconds = max(int(seconds), 0)

    if seconds < 60:
        return f"{seconds} sec"

    minutes = seconds // 60

    if minutes < 60:
        return f"{minutes} min"

    hours = minutes // 60

    if hours < 24:
        remaining_minutes = minutes % 60

        if remaining_minutes:
            return f"{hours} hr {remaining_minutes} min"

        return f"{hours} hr"

    days = hours // 24

    if days == 1:
        return "1 day"

    return f"{days} days"


def calculate_freshness_status(
    latest_matched_time,
    now=None,
    warning_after_seconds=120,
    stale_after_seconds=300,
):
    current_time = normalize_current_time(now)
    latest_time = normalize_timestamp(latest_matched_time)
    market_is_open = is_market_open_at(current_time)

    if latest_time is None:
        return {
            "level": "no_data",
            "label": "No Data",
            "message": "No matched quote data is available yet.",
            "age_seconds": None,
            "market_is_open": market_is_open,
        }

    current_time_naive = current_time.replace(tzinfo=None)
    age_seconds = max(int((current_time_naive - latest_time).total_seconds()), 0)

    if not market_is_open:
        return {
            "level": "closed",
            "label": "Market Closed",
            "message": "Market is closed; live updates are not expected.",
            "age_seconds": age_seconds,
            "market_is_open": False,
        }

    if age_seconds <= warning_after_seconds:
        return {
            "level": "fresh",
            "label": "Fresh",
            "message": "Live matched quote data is current.",
            "age_seconds": age_seconds,
            "market_is_open": True,
        }

    if age_seconds <= stale_after_seconds:
        return {
            "level": "delayed",
            "label": "Delayed",
            "message": "Matched quote data is falling behind.",
            "age_seconds": age_seconds,
            "market_is_open": True,
        }

    return {
        "level": "stale",
        "label": "Stale",
        "message": "Matched quote data is stale during market hours.",
        "age_seconds": age_seconds,
        "market_is_open": True,
    }


def get_latest_component_event(events_df, component):
    if events_df is None or events_df.empty:
        return None

    component_events = events_df[events_df["component"] == component]

    if component_events.empty:
        return None

    return component_events.iloc[0].to_dict()
