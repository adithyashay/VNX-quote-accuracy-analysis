import unittest
from datetime import datetime
from decimal import Decimal

from src.database.postgres_matcher import (
    load_delayed_rows_for_vnx_window,
    normalize_quote_dataframe,
)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = None
        self.params = None

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rows


class PostgresMatcherTests(unittest.TestCase):
    def test_normalize_quote_dataframe_parses_times_and_numbers(self):
        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "symbol": "AAPL",
                    "vnx_price": Decimal("101.25"),
                    "timestamp_readable": "2026-06-18 12:00:00",
                },
                {
                    "symbol": "MSFT",
                    "vnx_price": "bad",
                    "timestamp_readable": "not a timestamp",
                },
            ]
        )

        normalized_df = normalize_quote_dataframe(
            df,
            time_columns=["timestamp_readable"],
            number_columns=["vnx_price"],
        )

        self.assertEqual(len(normalized_df), 1)
        self.assertEqual(normalized_df.loc[0, "symbol"], "AAPL")
        self.assertEqual(normalized_df.loc[0, "vnx_price"], 101.25)

    def test_load_delayed_rows_for_vnx_window_adds_padding(self):
        import pandas as pd

        vnx_df = pd.DataFrame(
            [
                {
                    "symbol": "AAPL",
                    "timestamp_readable": datetime(2026, 6, 18, 12, 0, 0),
                },
                {
                    "symbol": "MSFT",
                    "timestamp_readable": datetime(2026, 6, 18, 12, 5, 0),
                },
            ]
        )
        cursor = FakeCursor(
            [
                (
                    "AAPL",
                    Decimal("101.10"),
                    datetime(2026, 6, 18, 11, 59, 30),
                )
            ]
        )

        delayed_df = load_delayed_rows_for_vnx_window(
            cursor,
            vnx_df,
            padding_seconds=60,
        )

        self.assertIn("delayed_time_readable", delayed_df.columns)
        self.assertEqual(cursor.params[0], datetime(2026, 6, 18, 11, 59, 0))
        self.assertEqual(cursor.params[1], datetime(2026, 6, 18, 12, 6, 0))


if __name__ == "__main__":
    unittest.main()
