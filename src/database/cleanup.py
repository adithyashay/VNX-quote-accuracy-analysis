import argparse

from src.database.connection import get_connection


QUOTE_TABLES = [
    "matched_quote_analysis",
    "vnx_quotes",
    "delayed_quotes",
]


def fetch_symbols_outside_universe(cursor, table_name):
    cursor.execute(
        f"""
        SELECT t.symbol, COUNT(*)
        FROM {table_name} t
        LEFT JOIN sp500_symbols s
            ON t.symbol = s.symbol
        WHERE s.symbol IS NULL
        GROUP BY t.symbol
        ORDER BY t.symbol;
        """
    )

    return cursor.fetchall()


def delete_symbols(cursor, table_name, symbols):
    if not symbols:
        return 0

    cursor.execute(
        f"""
        DELETE FROM {table_name}
        WHERE symbol = ANY(%s);
        """,
        (symbols,),
    )

    return cursor.rowcount


def cleanup_symbol_drift(apply=False):
    """
    Remove quote rows whose symbol is not in sp500_symbols.

    Runs in dry-run mode by default. Pass apply=True to delete rows.
    """

    results = {}

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for table_name in QUOTE_TABLES:
                outside_rows = fetch_symbols_outside_universe(cursor, table_name)
                symbols = [symbol for symbol, _ in outside_rows]

                if apply:
                    deleted_rows = delete_symbols(cursor, table_name, symbols)
                else:
                    deleted_rows = 0

                results[table_name] = {
                    "outside_rows": outside_rows,
                    "deleted_rows": deleted_rows,
                }

        if apply:
            connection.commit()

    return results


def print_cleanup_results(results, apply=False):
    mode = "APPLY" if apply else "DRY RUN"
    print(f"Symbol drift cleanup mode: {mode}")
    print()

    for table_name, result in results.items():
        outside_rows = result["outside_rows"]

        print(table_name)
        print("-" * len(table_name))

        if not outside_rows:
            print("No outside-universe symbols found.")
        else:
            for symbol, row_count in outside_rows:
                print(f"{symbol}: {row_count:,} rows")

        if apply:
            print(f"Deleted rows: {result['deleted_rows']:,}")

        print()


def main():
    parser = argparse.ArgumentParser(
        description="Find or remove quote rows outside sp500_symbols."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete outside-universe rows. Omit for dry-run mode.",
    )

    args = parser.parse_args()
    results = cleanup_symbol_drift(apply=args.apply)
    print_cleanup_results(results, apply=args.apply)


if __name__ == "__main__":
    main()
