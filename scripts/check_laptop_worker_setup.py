import os

from src.database.connection import get_connection
from src.settings import get_database_url, get_int_env


def check_env_value(name, required=True):
    value = os.getenv(name)

    if value:
        print(f"{name}: configured")
        return True

    if required:
        print(f"{name}: MISSING")
        return False

    print(f"{name}: not configured")
    return True


def fetch_scalar(cursor, query):
    cursor.execute(query)

    return cursor.fetchone()[0]


def table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = %s
        );
        """,
        (table_name,),
    )

    return cursor.fetchone()[0]


def check_database(label, database_url=None, require_snapshot_audit=False):
    try:
        with get_connection(database_url=database_url) as connection:
            with connection.cursor() as cursor:
                database_name = fetch_scalar(cursor, "SELECT current_database();")
                print(f"{label}: connected to {database_name}")

                table_names = [
                    "sp500_symbols",
                    "vnx_quotes",
                    "delayed_quotes",
                    "matched_quote_analysis",
                    "pipeline_health_events",
                ]

                if require_snapshot_audit:
                    table_names.append("quote_snapshot_audit")

                for table_name in table_names:
                    exists = table_exists(cursor, table_name)
                    print(f"{label}.{table_name}: {'ok' if exists else 'missing'}")

        return True

    except Exception as error:
        print(f"{label}: FAILED - {error}")
        return False


def main():
    print("Laptop Worker Setup Check")
    print("=========================")

    ok = True

    ok = check_env_value("VIANEXUS_API_TOKEN") and ok

    try:
        primary_url = get_database_url()
        print("Primary DATABASE_URL: configured")
    except Exception as error:
        primary_url = None
        ok = False
        print("Primary DATABASE_URL: MISSING")
        print("Primary database error:", error)

    replica_url = os.getenv("MATCHED_REPLICA_DATABASE_URL")
    ok = check_env_value("MATCHED_REPLICA_DATABASE_URL") and ok

    print()
    print("Pipeline Settings")
    print("-----------------")
    for name, default, min_value in [
        ("COLLECTION_INTERVAL_SECONDS", 60, 1),
        ("MATCHER_INTERVAL_SECONDS", 300, 1),
        ("MATCHER_VALID_WINDOW_SECONDS", 60, 1),
        ("RAW_RETENTION_DAYS", 0, 0),
        ("MATCHED_RETENTION_DAYS", 0, 0),
    ]:
        value = get_int_env(name, default, min_value=min_value)
        print(f"{name}: {value}")

    print(f"SAVE_CSV_BACKUP: {os.getenv('SAVE_CSV_BACKUP', 'false')}")

    print()
    print("Database Checks")
    print("---------------")

    if primary_url:
        ok = check_database(
            "local_primary",
            require_snapshot_audit=True,
        ) and ok

    if replica_url:
        ok = check_database("neon_replica", database_url=replica_url) and ok

    print()
    if ok:
        print("Setup check passed.")
    else:
        print("Setup check found issues. Fix them before running the market pipeline.")

    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
