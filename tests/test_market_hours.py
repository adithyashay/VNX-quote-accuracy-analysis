from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from src.market_hours import is_market_open_at


class MarketHoursTests(unittest.TestCase):
    def test_market_is_open_during_regular_weekday_hours(self):
        current_time = datetime(
            2026,
            6,
            17,
            10,
            0,
            tzinfo=ZoneInfo("America/New_York"),
        )

        self.assertTrue(is_market_open_at(current_time))

    def test_market_is_closed_before_open(self):
        current_time = datetime(
            2026,
            6,
            17,
            9,
            0,
            tzinfo=ZoneInfo("America/New_York"),
        )

        self.assertFalse(is_market_open_at(current_time))

    def test_market_is_closed_on_weekends(self):
        current_time = datetime(
            2026,
            6,
            20,
            10,
            0,
            tzinfo=ZoneInfo("America/New_York"),
        )

        self.assertFalse(is_market_open_at(current_time))


if __name__ == "__main__":
    unittest.main()
