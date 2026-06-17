import argparse
import os
from pathlib import Path

from src.database.schema import create_tables
from src.database.snapshot import (
    TABLE_SPECS,
    build_column_list,
    build_import_query,
    count_rows,
    get_snapshot_connection,
    quote_identifier,
)


def import_table(cursor, snapshot_dir, spec):
    input_file = snapshot_dir / f"{spec.table_name}.csv"

    if not input_file.exists():
        print(f"Skipping missing snapshot file: {input_file}")
        return 0

    staging_table_name = f"staging_{spec.table_name}"
    columns = build_column_list(spec.columns)

    cursor.execute(f"DROP TABLE IF EXISTS {quote_identifier(staging_table_name)};")
    cursor.execute(
        f"""
        CREATE TEMP TABLE {quote_identifier(staging_table_name)} AS
        SELECT {columns}
        FROM {quote_identifier(spec.table_name)}
        WITH NO DATA;
        """
    )

    with input_file.open("r", encoding="utf-8", newline="") as file:
        cursor.copy_expert(
            (
                f"COPY {quote_identifier(staging_table_name)} ({columns}) "
                "FROM STDIN WITH CSV HEADER"
            ),
            file,
        )

    cursor.execute(build_import_query(spec, staging_table_name))
    imported_rows = cursor.rowcount
    cursor.execute(f"DROP TABLE {quote_identifier(staging_table_name)};")

    return imported_rows


def import_postgres_snapshot(snapshot_dir):
    """
    Import exported history into the target PostgreSQL database.

    Requires TARGET_DATABASE_URL. The script sets DATABASE_URL to that value
    before creating tables so existing schema helpers target the cloud DB.
    """

    snapshot_dir = Path(snapshot_dir)

    if not snapshot_dir.exists():
        raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")

    target_database_url = os.getenv("TARGET_DATABASE_URL")

    if not target_database_url:
        raise ValueError("Missing required environment variable: TARGET_DATABASE_URL")

    os.environ["DATABASE_URL"] = target_database_url

    create_tables()

    with get_snapshot_connection("TARGET_DATABASE_URL") as connection:
        with connection.cursor() as cursor:
            for spec in TABLE_SPECS:
                imported_rows = import_table(cursor, snapshot_dir, spec)
                total_rows = count_rows(cursor, spec.table_name)

                print(
                    f"Imported {spec.table_name}: "
                    f"{imported_rows:,} rows processed; "
                    f"{total_rows:,} total rows in target"
                )

        connection.commit()

    print("Snapshot import completed:", snapshot_dir)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "snapshot_dir",
        help="Path to the exported snapshot directory.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    import_postgres_snapshot(args.snapshot_dir)
