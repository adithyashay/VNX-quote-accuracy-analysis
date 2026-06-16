import psycopg2

from src.settings import get_psycopg_database_url


def get_connection():
    """
    Create and return a PostgreSQL database connection.

    Database settings are loaded from DATABASE_URL or PostgreSQL env fields.
    """

    return psycopg2.connect(get_psycopg_database_url())
