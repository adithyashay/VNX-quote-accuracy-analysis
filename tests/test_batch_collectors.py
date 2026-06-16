import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

from src.batch_collectors import (
    collect_vnx_quotes_batch,
    keep_valid_symbol_rows,
    keep_valid_symbols,
    save_rows_to_csv,
)


class BatchCollectorValidationTests(unittest.TestCase):
    def test_keep_valid_symbols_allows_common_ticker_variants(self):
        df = pd.DataFrame(
            {
                "symbol": ["aapl", "BRK.B", "BF-B", "5.14"],
                "price": [1, 2, 3, 4],
            }
        )

        cleaned_df, invalid_rows = keep_valid_symbols(df)

        self.assertEqual(invalid_rows, 1)
        self.assertEqual(cleaned_df["symbol"].tolist(), ["AAPL", "BRK.B", "BF-B"])

    def test_keep_valid_symbol_rows_filters_invalid_symbols(self):
        rows = [
            {"symbol": " msft ", "price": 1},
            {"symbol": "5.14", "price": 2},
        ]

        cleaned_rows, invalid_rows = keep_valid_symbol_rows(rows)

        self.assertEqual(invalid_rows, 1)
        self.assertEqual(cleaned_rows, [{"symbol": "MSFT", "price": 1}])

    def test_collect_vnx_quotes_can_skip_csv_backup(self):
        quotes = [
            {
                "symbol": "aapl",
                "vnx_price": 100,
                "bid_price": 99,
                "ask_price": 101,
                "last_sale_price": 100,
                "timestamp_raw": 1,
                "timestamp_readable": "2026-06-16 09:30:00",
                "price_type": "REALTIME",
            },
            {
                "symbol": "5.14",
                "vnx_price": 200,
                "bid_price": 199,
                "ask_price": 201,
                "last_sale_price": 200,
                "timestamp_raw": 2,
                "timestamp_readable": "2026-06-16 09:30:00",
                "price_type": "REALTIME",
            },
        ]

        with patch("src.batch_client.get_vnx_quotes_batch", return_value=quotes):
            status = collect_vnx_quotes_batch(["AAPL", "BAD"], save_csv_backup=False)

        self.assertEqual(status["reason"], "CSV backup disabled")
        self.assertEqual(status["saved_rows"], 0)
        self.assertEqual(status["invalid_symbol_rows"], 1)
        self.assertEqual(status["collected_rows"], 1)
        self.assertEqual(status["rows"][0]["symbol"], "AAPL")

    def test_save_rows_to_csv_creates_backup_directory(self):
        with TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nested", "quotes.csv")

            status = save_rows_to_csv(
                rows=[{"symbol": "AAPL", "timestamp_raw": 1, "price": 100}],
                file_path=file_path,
                duplicate_columns=["symbol", "timestamp_raw"],
            )

            self.assertEqual(status["saved_rows"], 1)
            self.assertTrue(os.path.exists(file_path))


if __name__ == "__main__":
    unittest.main()
