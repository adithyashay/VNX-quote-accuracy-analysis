import os
import unittest
from unittest.mock import patch

from src.settings import (
    get_bool_env,
    get_database_url,
    get_int_env,
    get_sqlalchemy_database_url,
    normalize_postgres_url_for_psycopg,
    normalize_postgres_url_for_sqlalchemy,
)


class SettingsTests(unittest.TestCase):
    def test_database_url_takes_precedence(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgres://u:p@h:5432/db"}, clear=True):
            self.assertEqual(get_database_url(), "postgres://u:p@h:5432/db")

    def test_split_postgres_fields_build_database_url(self):
        env = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "quotes",
            "POSTGRES_USER": "quote user",
            "POSTGRES_PASSWORD": "pass/word",
        }

        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                get_database_url(),
                "postgresql://quote+user:pass%2Fword@localhost:5432/quotes",
            )

    def test_psycopg_url_normalization_accepts_legacy_postgres_scheme(self):
        self.assertEqual(
            normalize_postgres_url_for_psycopg("postgres://u:p@h/db"),
            "postgresql://u:p@h/db",
        )

    def test_sqlalchemy_url_normalization_sets_driver(self):
        self.assertEqual(
            normalize_postgres_url_for_sqlalchemy("postgresql://u:p@h/db"),
            "postgresql+psycopg2://u:p@h/db",
        )

    def test_get_sqlalchemy_database_url_uses_database_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgres://u:p@h/db"}, clear=True):
            self.assertEqual(
                get_sqlalchemy_database_url(),
                "postgresql+psycopg2://u:p@h/db",
            )

    def test_get_bool_env_reads_common_values(self):
        true_values = ["1", "true", "YES", "y", "on"]
        false_values = ["0", "false", "NO", "n", "off"]

        for value in true_values:
            with self.subTest(value=value):
                with patch.dict(os.environ, {"FLAG": value}, clear=True):
                    self.assertTrue(get_bool_env("FLAG"))

        for value in false_values:
            with self.subTest(value=value):
                with patch.dict(os.environ, {"FLAG": value}, clear=True):
                    self.assertFalse(get_bool_env("FLAG", default=True))

    def test_get_bool_env_uses_default_and_rejects_invalid_values(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(get_bool_env("MISSING_FLAG", default=True))

        with patch.dict(os.environ, {"FLAG": "maybe"}, clear=True):
            with self.assertRaises(ValueError):
                get_bool_env("FLAG")

    def test_get_int_env_reads_default_and_minimum(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_int_env("COUNT", 5, min_value=1), 5)

        with patch.dict(os.environ, {"COUNT": "12"}, clear=True):
            self.assertEqual(get_int_env("COUNT", 5, min_value=1), 12)

    def test_get_int_env_rejects_invalid_values(self):
        with patch.dict(os.environ, {"COUNT": "abc"}, clear=True):
            with self.assertRaises(ValueError):
                get_int_env("COUNT", 5)

        with patch.dict(os.environ, {"COUNT": "0"}, clear=True):
            with self.assertRaises(ValueError):
                get_int_env("COUNT", 5, min_value=1)


if __name__ == "__main__":
    unittest.main()
