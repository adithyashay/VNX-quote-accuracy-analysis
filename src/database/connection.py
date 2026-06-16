import os
import psycopg2
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    """
    Create and return a PostgreSQL database connection.

    Database settings are loaded from the .env file.
    """

    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    database = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")

    missing_values = []

    if not host:
        missing_values.append("POSTGRES_HOST")
    if not port:
        missing_values.append("POSTGRES_PORT")
    if not database:
        missing_values.append("POSTGRES_DB")
    if not user:
        missing_values.append("POSTGRES_USER")
    if not password:
        missing_values.append("POSTGRES_PASSWORD")

    if missing_values:
        raise ValueError(
            "Missing PostgreSQL settings in .env: "
            + ", ".join(missing_values)
        )

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password
    )