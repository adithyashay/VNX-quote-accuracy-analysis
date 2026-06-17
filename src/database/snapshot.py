from dataclasses import dataclass
from pathlib import Path

import psycopg2

from src.settings import normalize_postgres_url_for_psycopg, require_env


SNAPSHOT_DIR = Path(".migration")


@dataclass(frozen=True)
class TableSnapshotSpec:
    table_name: str
    columns: tuple[str, ...]
    conflict_columns: tuple[str, ...]
    order_by: tuple[str, ...]


TABLE_SPECS = [
    TableSnapshotSpec(
        table_name="sp500_symbols",
        columns=("symbol", "company_name", "sector", "sub_industry"),
        conflict_columns=("symbol",),
        order_by=("symbol",),
    ),
    TableSnapshotSpec(
        table_name="matched_quote_analysis",
        columns=(
            "symbol",
            "vnx_price",
            "vnx_time",
            "delayed_price",
            "delayed_time",
            "time_gap_seconds",
            "valid_match",
            "difference",
            "percentage_error",
            "absolute_percentage_error",
        ),
        conflict_columns=("symbol", "vnx_time"),
        order_by=("vnx_time", "symbol"),
    ),
]


def get_snapshot_connection(env_name):
    return psycopg2.connect(
        normalize_postgres_url_for_psycopg(require_env(env_name))
    )


def quote_identifier(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def build_column_list(columns):
    return ", ".join(quote_identifier(column) for column in columns)


def build_export_query(spec):
    columns = build_column_list(spec.columns)
    order_by = build_column_list(spec.order_by)

    return (
        f"COPY (SELECT {columns} FROM {quote_identifier(spec.table_name)} "
        f"ORDER BY {order_by}) TO STDOUT WITH CSV HEADER"
    )


def build_import_query(spec, staging_table_name):
    columns = build_column_list(spec.columns)
    conflict_columns = build_column_list(spec.conflict_columns)
    update_columns = [
        column
        for column in spec.columns
        if column not in spec.conflict_columns
    ]
    update_assignments = ", ".join(
        f"{quote_identifier(column)} = EXCLUDED.{quote_identifier(column)}"
        for column in update_columns
    )

    return f"""
        INSERT INTO {quote_identifier(spec.table_name)} ({columns})
        SELECT {columns}
        FROM {quote_identifier(staging_table_name)}
        ON CONFLICT ({conflict_columns})
        DO UPDATE SET {update_assignments};
    """


def count_rows(cursor, table_name):
    cursor.execute(f"SELECT COUNT(*) FROM {quote_identifier(table_name)};")

    return cursor.fetchone()[0]
