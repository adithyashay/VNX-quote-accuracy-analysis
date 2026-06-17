from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from src.dashboard.health import calculate_freshness_status, format_age


EASTERN_TIMEZONE = ZoneInfo("America/New_York")


class DashboardHealthTests(unittest.TestCase):
    def test_freshness_status_is_fresh_during_market_hours(self):
        status = calculate_freshness_status(
            latest_matched_time=datetime(2026, 6, 17, 9, 59, 30),
            now=datetime(2026, 6, 17, 10, 0, 0, tzinfo=EASTERN_TIMEZONE),
        )

        self.assertEqual(status["level"], "fresh")
        self.assertEqual(status["age_seconds"], 30)

    def test_freshness_status_is_delayed_during_market_hours(self):
        status = calculate_freshness_status(
            latest_matched_time=datetime(2026, 6, 17, 9, 57, 0),
            now=datetime(2026, 6, 17, 10, 0, 0, tzinfo=EASTERN_TIMEZONE),
        )

        self.assertEqual(status["level"], "delayed")
        self.assertEqual(status["age_seconds"], 180)

    def test_freshness_status_is_stale_during_market_hours(self):
        status = calculate_freshness_status(
            latest_matched_time=datetime(2026, 6, 17, 9, 50, 0),
            now=datetime(2026, 6, 17, 10, 0, 0, tzinfo=EASTERN_TIMEZONE),
        )

        self.assertEqual(status["level"], "stale")
        self.assertEqual(status["age_seconds"], 600)

    def test_freshness_status_respects_closed_market(self):
        status = calculate_freshness_status(
            latest_matched_time=datetime(2026, 6, 17, 15, 59, 0),
            now=datetime(2026, 6, 17, 18, 0, 0, tzinfo=EASTERN_TIMEZONE),
        )

        self.assertEqual(status["level"], "closed")
        self.assertFalse(status["market_is_open"])

    def test_freshness_status_handles_missing_data(self):
        status = calculate_freshness_status(
            latest_matched_time=None,
            now=datetime(2026, 6, 17, 10, 0, 0, tzinfo=EASTERN_TIMEZONE),
        )

        self.assertEqual(status["level"], "no_data")
        self.assertIsNone(status["age_seconds"])

    def test_format_age_uses_readable_units(self):
        self.assertEqual(format_age(45), "45 sec")
        self.assertEqual(format_age(180), "3 min")
        self.assertEqual(format_age(3900), "1 hr 5 min")
        self.assertEqual(format_age(172800), "2 days")


if __name__ == "__main__":
    unittest.main()
