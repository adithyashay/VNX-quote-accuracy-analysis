import psycopg2

from src.settings import get_psycopg_database_url, normalize_postgres_url_for_psycopg


def get_connection(database_url=None):
    """
    Create and return a PostgreSQL database connection.

    Database settings are loaded from DATABASE_URL or PostgreSQL env fields.
    """

    if database_url:
        return psycopg2.connect(normalize_postgres_url_for_psycopg(database_url))

    return psycopg2.connect(get_psycopg_database_url())
