from datetime import datetime
import unittest

from src.collection_audit import (
    build_snapshot_audit_rows,
    summarize_snapshot_audit_rows,
)


class CollectionAuditTests(unittest.TestCase):
    def test_build_snapshot_audit_rows_records_missing_symbols(self):
        rows = build_snapshot_audit_rows(
            source="vnx",
            requested_symbols=["AAPL", "MSFT"],
            returned_rows=[
                {
                    "symbol": "AAPL",
                    "vnx_price": 100.0,
                    "timestamp_readable": datetime(2026, 6, 29, 10, 0, 0),
                }
            ],
            cycle_id=datetime(2026, 6, 29, 10, 0, 30),
            batch_number=1,
            timestamp_field="timestamp_readable",
            price_field="vnx_price",
        )

        by_symbol = {row["symbol"]: row for row in rows}

        self.assertEqual(by_symbol["AAPL"]["status"], "ok")
        self.assertTrue(by_symbol["AAPL"]["returned"])
        self.assertEqual(by_symbol["AAPL"]["source_age_seconds"], 30)
        self.assertEqual(by_symbol["MSFT"]["status"], "missing_from_response")
        self.assertFalse(by_symbol["MSFT"]["returned"])

    def test_build_snapshot_audit_rows_records_api_errors(self):
        rows = build_snapshot_audit_rows(
            source="delayed",
            requested_symbols=["AAPL", "MSFT"],
            returned_rows=[],
            cycle_id=datetime(2026, 6, 29, 10, 0, 30),
            batch_number=1,
            timestamp_field="delayed_time_readable",
            price_field="delayed_price",
            error_message="timeout",
        )

        self.assertEqual({row["status"] for row in rows}, {"api_error"})
        self.assertEqual({row["reason"] for row in rows}, {"timeout"})

    def test_build_snapshot_audit_rows_classifies_malformed_and_unexpected(self):
        rows = build_snapshot_audit_rows(
            source="vnx",
            requested_symbols=["AAPL", "MSFT", "GOOG"],
            returned_rows=[
                {
                    "symbol": "AAPL",
                    "vnx_price": None,
                    "timestamp_readable": datetime(2026, 6, 29, 10, 0, 0),
                },
                {
                    "symbol": "MSFT",
                    "vnx_price": 100.0,
                    "timestamp_readable": None,
                },
                {
                    "symbol": "TSLA",
                    "vnx_price": 200.0,
                    "timestamp_readable": datetime(2026, 6, 29, 10, 0, 0),
                },
            ],
            cycle_id=datetime(2026, 6, 29, 10, 0, 30),
            batch_number=1,
            timestamp_field="timestamp_readable",
            price_field="vnx_price",
        )

        by_symbol = {row["symbol"]: row for row in rows}

        self.assertEqual(by_symbol["AAPL"]["status"], "missing_price")
        self.assertEqual(by_symbol["MSFT"]["status"], "missing_timestamp")
        self.assertEqual(by_symbol["GOOG"]["status"], "missing_from_response")
        self.assertEqual(by_symbol["TSLA"]["status"], "unexpected_symbol")
        self.assertFalse(by_symbol["TSLA"]["requested"])

    def test_build_snapshot_audit_rows_classifies_stale_timestamps(self):
        rows = build_snapshot_audit_rows(
            source="vnx",
            requested_symbols=["AAPL", "MSFT"],
            returned_rows=[
                {
                    "symbol": "AAPL",
                    "vnx_price": 100.0,
                    "timestamp_readable": datetime(2026, 6, 29, 9, 50, 0),
                },
                {
                    "symbol": "MSFT",
                    "vnx_price": 200.0,
                    "timestamp_readable": datetime(2026, 6, 29, 9, 59, 0),
                },
            ],
            cycle_id=datetime(2026, 6, 29, 10, 0, 0),
            batch_number=1,
            timestamp_field="timestamp_readable",
            price_field="vnx_price",
            stale_after_seconds=300,
        )

        by_symbol = {row["symbol"]: row for row in rows}

        self.assertEqual(by_symbol["AAPL"]["status"], "stale_timestamp")
        self.assertEqual(by_symbol["AAPL"]["source_age_seconds"], 600)
        self.assertEqual(by_symbol["MSFT"]["status"], "ok")

    def test_summarize_snapshot_audit_rows_groups_by_source(self):
        rows = build_snapshot_audit_rows(
            source="vnx",
            requested_symbols=["AAPL", "MSFT"],
            returned_rows=[
                {
                    "symbol": "AAPL",
                    "vnx_price": 100.0,
                    "timestamp_readable": datetime(2026, 6, 29, 10, 0, 0),
                }
            ],
            cycle_id=datetime(2026, 6, 29, 10, 0, 30),
            batch_number=1,
            timestamp_field="timestamp_readable",
            price_field="vnx_price",
        )

        summary = summarize_snapshot_audit_rows(rows)

        self.assertEqual(summary["vnx"]["requested_count"], 2)
        self.assertEqual(summary["vnx"]["returned_count"], 1)
        self.assertEqual(summary["vnx"]["ok_count"], 1)
        self.assertEqual(summary["vnx"]["missing_count"], 1)
        self.assertEqual(
            summary["vnx"]["symbols_by_status"],
            {"missing_from_response": ["MSFT"]},
        )

    def test_summarize_snapshot_audit_rows_includes_unexpected_symbols(self):
        rows = build_snapshot_audit_rows(
            source="vnx",
            requested_symbols=["AAPL"],
            returned_rows=[
                {
                    "symbol": "AAPL",
                    "vnx_price": 100.0,
                    "timestamp_readable": datetime(2026, 6, 29, 10, 0, 0),
                },
                {
                    "symbol": "TSLA",
                    "vnx_price": 200.0,
                    "timestamp_readable": datetime(2026, 6, 29, 10, 0, 0),
                },
            ],
            cycle_id=datetime(2026, 6, 29, 10, 0, 30),
            batch_number=1,
            timestamp_field="timestamp_readable",
            price_field="vnx_price",
        )

        summary = summarize_snapshot_audit_rows(rows)

        self.assertEqual(summary["vnx"]["requested_count"], 1)
        self.assertEqual(summary["vnx"]["returned_count"], 1)
        self.assertEqual(summary["vnx"]["problem_count"], 1)
        self.assertEqual(
            summary["vnx"]["symbols_by_status"],
            {"unexpected_symbol": ["TSLA"]},
        )


if __name__ == "__main__":
    unittest.main()
