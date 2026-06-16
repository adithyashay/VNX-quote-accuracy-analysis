import unittest

import pandas as pd

from src.batch_collectors import keep_valid_symbols


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


if __name__ == "__main__":
    unittest.main()
