import json
import unittest

import pandas as pd

from src.dashboard.coverage import (
    build_collection_coverage_tables,
    calculate_collection_cycle_metrics,
    calculate_repeated_problem_symbols,
)


class DashboardCoverageTests(unittest.TestCase):
    def test_build_collection_coverage_tables_extracts_feed_and_problem_rows(self):
        details = {
            "cycle_started_at": "2026-06-29T10:00:00",
            "snapshot_coverage": {
                "vnx": {
                    "requested_count": 3,
                    "returned_count": 2,
                    "ok_count": 1,
                    "problem_count": 2,
                    "missing_count": 1,
                    "source_timestamp_min": "2026-06-29T09:59:58",
                    "source_timestamp_max": "2026-06-29T10:00:00",
                    "symbols_by_status": {
                        "missing_from_response": ["MSFT"],
                        "missing_price": ["AAPL"],
                    },
                },
                "delayed": {
                    "requested_count": 3,
                    "returned_count": 3,
                    "ok_count": 2,
                    "problem_count": 1,
                    "missing_count": 0,
                    "source_timestamp_min": "2026-06-29T09:59:55",
                    "source_timestamp_max": "2026-06-29T10:00:00",
                    "symbols_by_status": {
                        "unexpected_symbol": ["TSLA"],
                    },
                },
            },
        }
        history_df = pd.DataFrame(
            [
                {
                    "event_time": "2026-06-29T10:00:30",
                    "status": "warning",
                    "details": json.dumps(details),
                }
            ]
        )

        coverage_df, problem_df = build_collection_coverage_tables(history_df)

        self.assertEqual(len(coverage_df), 2)
        self.assertEqual(set(coverage_df["source"]), {"VNX", "DELAYED"})
        self.assertEqual(coverage_df["requested_count"].sum(), 6)
        self.assertEqual(coverage_df["missing_count"].sum(), 1)
        self.assertEqual(
            set(problem_df["problem"]),
            {"missing_from_response", "missing_price", "unexpected_symbol"},
        )
        self.assertEqual(set(problem_df["symbol"]), {"MSFT", "AAPL", "TSLA"})

    def test_calculate_collection_cycle_metrics_counts_missing_cycles(self):
        coverage_df = pd.DataFrame(
            {
                "cycle_started_at": [
                    "2026-06-29T10:00:00",
                    "2026-06-29T10:00:00",
                    "2026-06-29T10:01:00",
                    "2026-06-29T10:01:00",
                    "2026-06-29T10:03:00",
                    "2026-06-29T10:03:00",
                ]
            }
        )

        metrics = calculate_collection_cycle_metrics(
            coverage_df,
            expected_interval_seconds=60,
        )

        self.assertEqual(metrics["expected_cycles"], 4)
        self.assertEqual(metrics["actual_cycles"], 3)
        self.assertEqual(metrics["missing_cycles"], 1)
        self.assertEqual(metrics["avg_cycle_gap_seconds"], 90)
        self.assertEqual(metrics["max_cycle_gap_seconds"], 120)

    def test_calculate_repeated_problem_symbols_groups_by_source_and_symbol(self):
        problem_df = pd.DataFrame(
            [
                {
                    "event_time": "2026-06-29T10:00:00",
                    "source": "VNX",
                    "problem": "missing_from_response",
                    "symbol": "MSFT",
                },
                {
                    "event_time": "2026-06-29T10:01:00",
                    "source": "VNX",
                    "problem": "missing_price",
                    "symbol": "MSFT",
                },
                {
                    "event_time": "2026-06-29T10:01:00",
                    "source": "DELAYED",
                    "problem": "missing_timestamp",
                    "symbol": "AAPL",
                },
            ]
        )

        repeated_df = calculate_repeated_problem_symbols(problem_df)

        top_row = repeated_df.iloc[0]

        self.assertEqual(top_row["source"], "VNX")
        self.assertEqual(top_row["symbol"], "MSFT")
        self.assertEqual(top_row["problem_count"], 2)
        self.assertEqual(
            top_row["problem_types"],
            "missing_from_response, missing_price",
        )


if __name__ == "__main__":
    unittest.main()
