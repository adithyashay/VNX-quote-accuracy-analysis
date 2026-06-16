import os
import unittest
from unittest.mock import patch

from src.settings import (
    get_database_url,
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


if __name__ == "__main__":
    unittest.main()
