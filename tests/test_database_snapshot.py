import unittest

from src.database.snapshot import (
    TABLE_SPECS,
    build_export_query,
    build_import_query,
)


class DatabaseSnapshotTests(unittest.TestCase):
    def test_snapshot_specs_include_historical_tables(self):
        table_names = [spec.table_name for spec in TABLE_SPECS]

        self.assertEqual(
            table_names,
            [
                "sp500_symbols",
                "matched_quote_analysis",
            ],
        )

    def test_export_query_uses_csv_header(self):
        query = build_export_query(TABLE_SPECS[1])

        self.assertIn("COPY", query)
        self.assertIn("FROM \"matched_quote_analysis\"", query)
        self.assertIn("WITH CSV HEADER", query)

    def test_import_query_uses_conflict_key(self):
        query = build_import_query(TABLE_SPECS[1], "staging_matched_quote_analysis")

        self.assertIn("ON CONFLICT (\"symbol\", \"vnx_time\")", query)
        self.assertIn("\"percentage_error\" = EXCLUDED.\"percentage_error\"", query)


if __name__ == "__main__":
    unittest.main()
