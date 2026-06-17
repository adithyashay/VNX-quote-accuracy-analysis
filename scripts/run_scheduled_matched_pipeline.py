from src.database.importer import import_sp500_symbols
from src.database.schema import create_tables
from src.pipeline.matched_only import run_matched_only_cycle


def main():
    create_tables()
    import_sp500_symbols()
    run_matched_only_cycle()


if __name__ == "__main__":
    main()
