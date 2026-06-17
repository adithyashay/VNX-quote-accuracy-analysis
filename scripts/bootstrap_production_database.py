from src.database.importer import import_sp500_symbols
from src.database.schema import create_tables


def bootstrap_production_database():
    """
    Create required tables and seed reference data for deployment.
    """

    create_tables()
    imported_symbols = import_sp500_symbols()

    print("Production database bootstrap completed.")
    print("S&P 500 symbols processed:", imported_symbols)


if __name__ == "__main__":
    bootstrap_production_database()
