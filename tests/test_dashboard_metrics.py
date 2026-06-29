import unittest

import pandas as pd

from src.dashboard.metrics import (
    add_cents_columns,
    calculate_error_threshold_summary,
    calculate_observation_interval_summary,
    calculate_overall_metrics,
    calculate_price_band_summary,
    calculate_symbol_metrics,
)


class DashboardMetricsTests(unittest.TestCase):
    def setUp(self):
        self.df = add_cents_columns(
            pd.DataFrame(
                [
                    {
                        "symbol": "AAPL",
                        "company_name": "Apple Inc.",
                        "sector": "Information Technology",
                        "sub_industry": "Technology Hardware",
                        "difference": 0.10,
                        "delayed_price": 200.00,
                        "percentage_error": 0.05,
                        "absolute_percentage_error": 0.05,
                        "time_gap_seconds": 0.4,
                        "vnx_time": "2026-06-17 09:30:05",
                    },
                    {
                        "symbol": "MSFT",
                        "company_name": "Microsoft",
                        "sector": "Information Technology",
                        "sub_industry": "Systems Software",
                        "difference": -0.03,
                        "delayed_price": 75.00,
                        "percentage_error": -0.01,
                        "absolute_percentage_error": 0.01,
                        "time_gap_seconds": 0.6,
                        "vnx_time": "2026-06-17 09:33:15",
                    },
                    {
                        "symbol": "AAPL",
                        "company_name": "Apple Inc.",
                        "sector": "Information Technology",
                        "sub_industry": "Technology Hardware",
                        "difference": 0.25,
                        "delayed_price": 210.00,
                        "percentage_error": 0.12,
                        "absolute_percentage_error": 0.12,
                        "time_gap_seconds": 0.9,
                        "vnx_time": "2026-06-17 09:36:01",
                    },
                ]
            )
        )

    def test_overall_metrics_use_cents_difference(self):
        metrics = calculate_overall_metrics(self.df)

        self.assertEqual(metrics["total_observations"], 3)
        self.assertEqual(metrics["symbols_analyzed"], 2)
        self.assertAlmostEqual(metrics["avg_price_error_cents"], 12.6666667)
        self.assertAlmostEqual(metrics["median_price_error_cents"], 10.0)
        self.assertAlmostEqual(metrics["p90_price_error_cents"], 22.0)
        self.assertAlmostEqual(metrics["p99_price_error_cents"], 24.7)
        self.assertAlmostEqual(metrics["max_price_error_cents"], 25.0)
        self.assertAlmostEqual(metrics["avg_directional_error_cents"], 10.6666667)
        self.assertAlmostEqual(metrics["median_price_error_bps"], 5.0)
        self.assertAlmostEqual(metrics["p90_price_error_bps"], 10.6)
        self.assertAlmostEqual(metrics["p95_price_error_bps"], 11.3)
        self.assertAlmostEqual(metrics["p99_price_error_bps"], 11.86)

    def test_symbol_metrics_sort_by_cents_difference(self):
        symbol_stats = calculate_symbol_metrics(self.df)

        self.assertEqual(symbol_stats.iloc[0]["symbol"], "MSFT")
        self.assertAlmostEqual(
            symbol_stats.iloc[0]["avg_price_error_cents"],
            3.0,
        )
        aapl_stats = symbol_stats[symbol_stats["symbol"] == "AAPL"].iloc[0]
        self.assertAlmostEqual(aapl_stats["p90_price_error_cents"], 23.5)
        self.assertAlmostEqual(aapl_stats["p99_price_error_cents"], 24.85)

    def test_cents_threshold_summary_counts_observations(self):
        threshold_df = calculate_error_threshold_summary(self.df)

        rows = threshold_df.set_index("threshold_cents")

        self.assertEqual(set(rows.index.tolist()), {20, 50, 70})
        self.assertEqual(rows.loc[20, "observations"], 2)
        self.assertEqual(rows.loc[50, "observations"], 3)
        self.assertEqual(rows.loc[70, "observations"], 3)

    def test_observation_interval_summary_counts_time_buckets(self):
        interval_df = calculate_observation_interval_summary(
            self.df,
            interval_minutes=5,
        )

        self.assertEqual(len(interval_df), 2)
        self.assertEqual(interval_df.iloc[0]["observations"], 2)
        self.assertEqual(interval_df.iloc[0]["symbols_analyzed"], 2)
        self.assertEqual(interval_df.iloc[1]["observations"], 1)
        self.assertEqual(interval_df.iloc[1]["symbols_analyzed"], 1)

    def test_price_band_summary_normalizes_by_reference_price(self):
        price_band_df = calculate_price_band_summary(self.df)
        rows = price_band_df.set_index("price_band")

        self.assertEqual(rows.loc["$50-$100", "observations"], 1)
        self.assertEqual(rows.loc["$100-$250", "observations"], 2)
        self.assertAlmostEqual(
            rows.loc["$100-$250", "median_price_error_cents"],
            17.5,
        )
        self.assertAlmostEqual(
            rows.loc["$100-$250", "median_price_error_bps"],
            8.5,
        )


if __name__ == "__main__":
    unittest.main()
