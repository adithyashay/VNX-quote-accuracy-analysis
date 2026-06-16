import unittest

import pandas as pd

from src.matcher import normalize_matched_dataframe, normalize_timestamp_key


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


if __name__ == "__main__":
    unittest.main()
