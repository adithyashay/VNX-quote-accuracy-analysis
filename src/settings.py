import os
from urllib.parse import quote_plus

from dotenv import load_dotenv


load_dotenv()


POSTGRES_ENV_VARS = [
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
]


def require_env(name):
    value = os.getenv(name)

    if not value:
        raise ValueError(f"Missing required environment variable: {name}")

    return value


def get_vianexus_api_token():
    return require_env("VIANEXUS_API_TOKEN")


def normalize_postgres_url_for_psycopg(url):
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]

    return url


def normalize_postgres_url_for_sqlalchemy(url):
    if url.startswith("postgresql+psycopg2://"):
        return url

    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]

    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]

    return url


def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    missing_values = [
        name
        for name in POSTGRES_ENV_VARS
        if not os.getenv(name)
    ]

    if missing_values:
        raise ValueError(
            "Missing PostgreSQL settings. Set DATABASE_URL or provide: "
            + ", ".join(missing_values)
        )

    user = quote_plus(os.getenv("POSTGRES_USER"))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD"))
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    database = os.getenv("POSTGRES_DB")

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_psycopg_database_url():
    return normalize_postgres_url_for_psycopg(get_database_url())


def get_sqlalchemy_database_url():
    return normalize_postgres_url_for_sqlalchemy(get_database_url())
