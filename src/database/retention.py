from src.database.connection import get_connection


def delete_older_than(cursor, table_name, timestamp_column, retention_days):
    if retention_days is None or retention_days <= 0:
        return 0

    query = f"""
        DELETE FROM {table_name}
        WHERE {timestamp_column} < (
            (CURRENT_TIMESTAMP AT TIME ZONE 'America/New_York')
            - (%s * INTERVAL '1 day')
        );
    """

    cursor.execute(query, (retention_days,))

    return cursor.rowcount


def prune_quote_history(raw_retention_days=0, matched_retention_days=0):
    """
    Prune quote history using day-based retention settings.

    Raw retention applies to vnx_quotes and delayed_quotes. Matched retention is
    optional and should usually remain 0 so long-term dashboard analysis stays.
    """

    summary = {
        "raw_retention_days": raw_retention_days,
        "matched_retention_days": matched_retention_days,
        "vnx_rows_deleted": 0,
        "delayed_rows_deleted": 0,
        "matched_rows_deleted": 0,
    }

    if raw_retention_days <= 0 and matched_retention_days <= 0:
        return summary

    with get_connection() as connection:
        with connection.cursor() as cursor:
            summary["vnx_rows_deleted"] = delete_older_than(
                cursor,
                "vnx_quotes",
                "timestamp_readable",
                raw_retention_days,
            )
            summary["delayed_rows_deleted"] = delete_older_than(
                cursor,
                "delayed_quotes",
                "delayed_time_readable",
                raw_retention_days,
            )
            summary["matched_rows_deleted"] = delete_older_than(
                cursor,
                "matched_quote_analysis",
                "vnx_time",
                matched_retention_days,
            )

        connection.commit()

    return summary
