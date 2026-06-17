import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.pipeline.matched_only import run_matched_only_cycle, split_into_batches


class MatchedOnlyPipelineTests(unittest.TestCase):
    def test_split_into_batches(self):
        batches = list(split_into_batches(["A", "B", "C"], 2))

        self.assertEqual(batches, [["A", "B"], ["C"]])

    @patch("src.pipeline.matched_only.safe_record_pipeline_event")
    @patch("src.pipeline.matched_only.prune_old_matched_rows", return_value=0)
    @patch("src.pipeline.matched_only.insert_matched_quote_rows", return_value=1)
    @patch("src.pipeline.matched_only.collect_delayed_quotes_batch")
    @patch("src.pipeline.matched_only.collect_vnx_quotes_batch")
    @patch("src.pipeline.matched_only.is_market_open_now")
    def test_run_matched_only_cycle_collects_matches_and_inserts_only_matches(
        self,
        mock_market_open,
        mock_collect_vnx,
        mock_collect_delayed,
        mock_insert_matches,
        mock_prune,
        mock_record_event,
    ):
        mock_market_open.return_value = (
            True,
            datetime(2026, 6, 17, 10, 0, tzinfo=ZoneInfo("America/New_York")),
        )
        mock_collect_vnx.return_value = {
            "rows": [
                {
                    "symbol": "AAPL",
                    "vnx_price": 100,
                    "timestamp_readable": datetime(2026, 6, 17, 9, 59, 30),
                }
            ]
        }
        mock_collect_delayed.return_value = {
            "rows": [
                {
                    "symbol": "AAPL",
                    "delayed_price": 99,
                    "delayed_time_readable": datetime(2026, 6, 17, 9, 59, 30),
                }
            ]
        }

        summary = run_matched_only_cycle(
            symbols=["AAPL"],
            batch_size=1,
            valid_window_seconds=60,
            retention_days=0,
        )

        self.assertEqual(summary["vnx_rows_collected"], 1)
        self.assertEqual(summary["delayed_rows_collected"], 1)
        self.assertEqual(summary["matched_rows_generated"], 1)
        self.assertEqual(summary["matched_rows_inserted"], 1)
        self.assertEqual(summary["valid_matches"], 1)
        mock_collect_vnx.assert_called_once_with(["AAPL"], save_csv_backup=False)
        mock_collect_delayed.assert_called_once_with(["AAPL"], save_csv_backup=False)
        mock_insert_matches.assert_called_once()

    @patch("src.pipeline.matched_only.safe_record_pipeline_event")
    @patch("src.pipeline.matched_only.is_market_open_now")
    def test_run_matched_only_cycle_skips_when_market_is_closed(
        self,
        mock_market_open,
        mock_record_event,
    ):
        mock_market_open.return_value = (
            False,
            datetime(2026, 6, 17, 18, 0, tzinfo=ZoneInfo("America/New_York")),
        )

        summary = run_matched_only_cycle(
            symbols=["AAPL"],
            batch_size=1,
            valid_window_seconds=60,
            retention_days=0,
        )

        self.assertFalse(summary["market_is_open"])
        self.assertEqual(summary["matched_rows_inserted"], 0)
        mock_record_event.assert_called_once()


if __name__ == "__main__":
    unittest.main()
