from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo


EASTERN_TIMEZONE = ZoneInfo("America/New_York")
MARKET_OPEN = dt_time(9, 30)
MARKET_CLOSE = dt_time(16, 0)


def get_current_eastern_time():
    return datetime.now(EASTERN_TIMEZONE)


def as_eastern_time(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=EASTERN_TIMEZONE)

    return value.astimezone(EASTERN_TIMEZONE)


def is_market_open_at(current_time):
    """
    Check regular US weekday market hours, using Eastern time.
    """

    eastern_time = as_eastern_time(current_time)

    is_weekday = eastern_time.weekday() < 5
    is_market_hours = MARKET_OPEN <= eastern_time.time() <= MARKET_CLOSE

    return is_weekday and is_market_hours


def is_market_open_now():
    current_time = get_current_eastern_time()

    return is_market_open_at(current_time), current_time
