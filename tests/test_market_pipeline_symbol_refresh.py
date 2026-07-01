from datetime import datetime
import unittest
from unittest.mock import patch

import scripts.run_market_pipeline as pipeline


class MarketPipelineSymbolRefreshTests(unittest.TestCase):
    def setUp(self):
        self.original_symbols = pipeline.SYMBOLS
        self.original_replica_url = pipeline.MATCHED_REPLICA_DATABASE_URL

    def tearDown(self):
        pipeline.SYMBOLS = self.original_symbols
        pipeline.MATCHED_REPLICA_DATABASE_URL = self.original_replica_url

    def test_refresh_symbol_universe_updates_local_replica_and_active_symbols(self):
        pipeline.SYMBOLS = ["OLD"]
        pipeline.MATCHED_REPLICA_DATABASE_URL = (
            "postgresql://replica_user:replica_pass@example.com/db"
        )

        with (
            patch("scripts.run_market_pipeline.download_sp500_symbols") as download,
            patch(
                "scripts.run_market_pipeline.import_sp500_symbols",
                side_effect=[503, 503],
            ) as import_symbols,
            patch(
                "scripts.run_market_pipeline.load_sp500_symbols",
                return_value=["AAPL", "MSFT", "NVDA"],
            ),
            patch("builtins.print"),
        ):
            summary = pipeline.refresh_sp500_symbol_universe_for_market_day(
                datetime(2026, 7, 1).date(),
            )

        download.assert_called_once_with()
        self.assertEqual(import_symbols.call_count, 2)
        import_symbols.assert_any_call()
        import_symbols.assert_any_call(
            database_url="postgresql://replica_user:replica_pass@example.com/db"
        )
        self.assertEqual(pipeline.SYMBOLS, ["AAPL", "MSFT", "NVDA"])
        self.assertEqual(summary["previous_symbol_count"], 1)
        self.assertEqual(summary["active_symbol_count"], 3)
        self.assertEqual(summary["local_symbols_imported"], 503)
        self.assertEqual(summary["replica_symbols_imported"], 503)

    def test_maybe_refresh_runs_only_once_per_market_day(self):
        current_time = datetime(2026, 7, 1, 9, 35)

        with (
            patch(
                "scripts.run_market_pipeline.refresh_sp500_symbol_universe_for_market_day",
                return_value={"replica_error": None},
            ) as refresh,
            patch("scripts.run_market_pipeline.write_pipeline_event"),
            patch("scripts.run_market_pipeline.write_replica_pipeline_event"),
            patch("builtins.print"),
        ):
            first_refresh_date = pipeline.maybe_refresh_sp500_symbol_universe(
                None,
                current_time,
            )
            second_refresh_date = pipeline.maybe_refresh_sp500_symbol_universe(
                first_refresh_date,
                current_time,
            )

        refresh.assert_called_once_with(current_time.date())
        self.assertEqual(first_refresh_date, current_time.date())
        self.assertEqual(second_refresh_date, current_time.date())


if __name__ == "__main__":
    unittest.main()
