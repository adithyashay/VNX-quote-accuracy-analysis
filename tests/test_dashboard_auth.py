import unittest

from src.dashboard.auth import credentials_match


class DashboardAuthTests(unittest.TestCase):
    def test_credentials_match_expected_values(self):
        self.assertTrue(
            credentials_match(
                "boss",
                "secret",
                "boss",
                "secret",
            )
        )

    def test_credentials_reject_wrong_values(self):
        self.assertFalse(
            credentials_match(
                "boss",
                "wrong",
                "boss",
                "secret",
            )
        )

        self.assertFalse(
            credentials_match(
                "wrong",
                "secret",
                "boss",
                "secret",
            )
        )

    def test_credentials_reject_missing_values(self):
        self.assertFalse(credentials_match("", "secret", "boss", "secret"))
        self.assertFalse(credentials_match("boss", "", "boss", "secret"))
        self.assertFalse(credentials_match("boss", "secret", "", "secret"))
        self.assertFalse(credentials_match("boss", "secret", "boss", ""))


if __name__ == "__main__":
    unittest.main()
