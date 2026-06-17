from datetime import datetime
import os
from pathlib import Path

from src.database.snapshot import (
    SNAPSHOT_DIR,
    TABLE_SPECS,
    build_export_query,
    count_rows,
    get_snapshot_connection,
)
from src.settings import get_psycopg_database_url


def export_postgres_snapshot(output_dir=None):
    """
    Export local PostgreSQL history into ignored CSV files.

    Uses SOURCE_DATABASE_URL if set. For normal local use, set:
    SOURCE_DATABASE_URL=<your local PostgreSQL URL>
    """

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = SNAPSHOT_DIR / f"postgres_snapshot_{timestamp}"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    if not os.getenv("SOURCE_DATABASE_URL"):
        os.environ["SOURCE_DATABASE_URL"] = get_psycopg_database_url()

    with get_snapshot_connection("SOURCE_DATABASE_URL") as connection:
        with connection.cursor() as cursor:
            for spec in TABLE_SPECS:
                output_file = output_dir / f"{spec.table_name}.csv"
                row_count = count_rows(cursor, spec.table_name)

                with output_file.open("w", encoding="utf-8", newline="") as file:
                    cursor.copy_expert(build_export_query(spec), file)

                print(
                    f"Exported {spec.table_name}: "
                    f"{row_count:,} rows -> {output_file}"
                )

    print("Snapshot export completed:", output_dir)

    return output_dir


if __name__ == "__main__":
    export_postgres_snapshot()
