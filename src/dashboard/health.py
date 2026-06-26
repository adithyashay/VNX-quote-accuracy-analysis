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


def calculate_age_seconds(latest_time, current_time):
    normalized_time = normalize_timestamp(latest_time)

    if normalized_time is None:
        return None

    current_time_naive = current_time.replace(tzinfo=None)

    return max(int((current_time_naive - normalized_time).total_seconds()), 0)


def calculate_freshness_status(
    latest_matched_time,
    latest_raw_time=None,
    now=None,
    collection_interval_seconds=60,
    matcher_interval_seconds=300,
    collection_grace_seconds=60,
    matcher_grace_seconds=120,
):
    current_time = normalize_current_time(now)
    market_is_open = is_market_open_at(current_time)
    matched_age_seconds = calculate_age_seconds(latest_matched_time, current_time)
    raw_age_seconds = calculate_age_seconds(latest_raw_time, current_time)

    if matched_age_seconds is None and raw_age_seconds is None:
        return {
            "level": "no_data",
            "label": "No Data",
            "message": "No quote data is available yet.",
            "age_seconds": None,
            "matched_age_seconds": None,
            "raw_age_seconds": None,
            "market_is_open": market_is_open,
        }

    if not market_is_open:
        return {
            "level": "closed",
            "label": "Market Closed",
            "message": "Market is closed; live updates are not expected.",
            "age_seconds": matched_age_seconds,
            "matched_age_seconds": matched_age_seconds,
            "raw_age_seconds": raw_age_seconds,
            "market_is_open": False,
        }

    raw_warning_after_seconds = max(
        collection_interval_seconds * 2,
        collection_interval_seconds + collection_grace_seconds,
    )
    raw_stale_after_seconds = max(
        collection_interval_seconds * 5,
        raw_warning_after_seconds + collection_grace_seconds,
    )

    matcher_on_schedule_after_seconds = (
        matcher_interval_seconds + matcher_grace_seconds
    )
    matcher_stale_after_seconds = (
        matcher_interval_seconds * 2 + matcher_grace_seconds
    )

    if raw_age_seconds is None:
        return {
            "level": "delayed",
            "label": "No Source Data",
            "message": "No VNX quote timestamps are available yet.",
            "age_seconds": matched_age_seconds,
            "matched_age_seconds": matched_age_seconds,
            "raw_age_seconds": None,
            "market_is_open": True,
        }

    if raw_age_seconds > raw_stale_after_seconds:
        return {
            "level": "stale",
            "label": "Source Timestamp Stale",
            "message": "The latest VNX quote timestamp is stale during market hours.",
            "age_seconds": raw_age_seconds,
            "matched_age_seconds": matched_age_seconds,
            "raw_age_seconds": raw_age_seconds,
            "market_is_open": True,
        }

    if raw_age_seconds > raw_warning_after_seconds:
        return {
            "level": "delayed",
            "label": "Source Timestamp Delayed",
            "message": "The latest VNX quote timestamp is falling behind.",
            "age_seconds": raw_age_seconds,
            "matched_age_seconds": matched_age_seconds,
            "raw_age_seconds": raw_age_seconds,
            "market_is_open": True,
        }

    if matched_age_seconds is None:
        return {
            "level": "delayed",
            "label": "Matcher Pending",
            "message": "Source data is live, but matched analysis has not run yet.",
            "age_seconds": None,
            "matched_age_seconds": None,
            "raw_age_seconds": raw_age_seconds,
            "market_is_open": True,
        }

    if matched_age_seconds <= matcher_on_schedule_after_seconds:
        return {
            "level": "fresh",
            "label": "On Schedule",
            "message": "Source data is live and matched analysis is within the matcher schedule.",
            "age_seconds": matched_age_seconds,
            "matched_age_seconds": matched_age_seconds,
            "raw_age_seconds": raw_age_seconds,
            "market_is_open": True,
        }

    if matched_age_seconds <= matcher_stale_after_seconds:
        return {
            "level": "delayed",
            "label": "Matcher Delayed",
            "message": "Source data is live, but matched analysis missed its expected schedule.",
            "age_seconds": matched_age_seconds,
            "matched_age_seconds": matched_age_seconds,
            "raw_age_seconds": raw_age_seconds,
            "market_is_open": True,
        }

    return {
        "level": "stale",
        "label": "Matcher Stale",
        "message": "Source data is live, but matched analysis is stale during market hours.",
        "age_seconds": matched_age_seconds,
        "matched_age_seconds": matched_age_seconds,
        "raw_age_seconds": raw_age_seconds,
        "market_is_open": True,
    }


def get_latest_component_event(events_df, component):
    if events_df is None or events_df.empty:
        return None

    component_events = events_df[events_df["component"] == component]

    if component_events.empty:
        return None

    return component_events.iloc[0].to_dict()
