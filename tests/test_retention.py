import unittest

from src.database.retention import delete_older_than


class FakeCursor:
    def __init__(self, rowcount=0):
        self.rowcount = rowcount
        self.executed = False
        self.query = None
        self.params = None

    def execute(self, query, params=None):
        self.executed = True
        self.query = query
        self.params = params


class RetentionTests(unittest.TestCase):
    def test_delete_older_than_skips_zero_retention(self):
        cursor = FakeCursor(rowcount=12)

        deleted_rows = delete_older_than(
            cursor,
            "vnx_quotes",
            "timestamp_readable",
            0,
        )

        self.assertEqual(deleted_rows, 0)
        self.assertFalse(cursor.executed)

    def test_delete_older_than_uses_day_interval(self):
        cursor = FakeCursor(rowcount=12)

        deleted_rows = delete_older_than(
            cursor,
            "vnx_quotes",
            "timestamp_readable",
            1,
        )

        self.assertEqual(deleted_rows, 12)
        self.assertTrue(cursor.executed)
        self.assertIn("DELETE FROM vnx_quotes", cursor.query)
        self.assertIn("America/New_York", cursor.query)
        self.assertEqual(cursor.params, (1,))


if __name__ == "__main__":
    unittest.main()
