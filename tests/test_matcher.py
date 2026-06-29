import unittest

import pandas as pd

from src.matcher import (
    match_vnx_rows_to_delayed,
    normalize_matched_dataframe,
    normalize_timestamp_key,
)


class MatcherNormalizationTests(unittest.TestCase):
    def test_timestamp_keys_ignore_microsecond_display_differences(self):
        timestamps = pd.Series(
            [
                "2026-06-05 15:22:23.544",
                "2026-06-05 15:22:23.544000",
            ]
        )

        keys = normalize_timestamp_key(timestamps)

        self.assertEqual(keys.iloc[0], keys.iloc[1])

    def test_normalize_matched_dataframe_keeps_closest_duplicate(self):
        matched_df = pd.DataFrame(
            [
                {
                    "symbol": "AAPL",
                    "vnx_time": "2026-06-05 15:22:23.544",
                    "delayed_time": "2026-06-05 15:23:10",
                    "time_gap_seconds": 46.456,
                },
                {
                    "symbol": "AAPL",
                    "vnx_time": "2026-06-05 15:22:23.544000",
                    "delayed_time": "2026-06-05 15:22:37",
                    "time_gap_seconds": 13.456,
                },
            ]
        )

        normalized_df = normalize_matched_dataframe(matched_df)

        self.assertEqual(len(normalized_df), 1)
        self.assertEqual(normalized_df.iloc[0]["time_gap_seconds"], 13.456)

    def test_matcher_marks_wide_timestamp_gap_invalid(self):
        vnx_df = pd.DataFrame(
            [
                {
                    "symbol": "AAPL",
                    "vnx_price": 100.0,
                    "timestamp_readable": pd.Timestamp("2026-06-29 10:00:00"),
                }
            ]
        )
        delayed_df = pd.DataFrame(
            [
                {
                    "symbol": "AAPL",
                    "delayed_price": 101.0,
                    "delayed_time_readable": pd.Timestamp(
                        "2026-06-29 10:02:00"
                    ),
                }
            ]
        )

        matched_df = match_vnx_rows_to_delayed(
            vnx_df,
            delayed_df,
            valid_window_seconds=60,
        )

        self.assertEqual(len(matched_df), 1)
        self.assertEqual(matched_df.iloc[0]["time_gap_seconds"], 120)
        self.assertFalse(bool(matched_df.iloc[0]["valid_match"]))


if __name__ == "__main__":
    unittest.main()
