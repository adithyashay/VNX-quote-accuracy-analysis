from src.database.connection import get_connection
from src.database.pipeline_health import create_pipeline_health_table


def create_tables():
    """
    Create PostgreSQL tables for the VNX quote accuracy project.
    """

    create_sp500_symbols_table = """
    CREATE TABLE IF NOT EXISTS sp500_symbols (
        symbol TEXT PRIMARY KEY,
        company_name TEXT,
        sector TEXT,
        sub_industry TEXT
    );
    """

    create_vnx_quotes_table = """
    CREATE TABLE IF NOT EXISTS vnx_quotes (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        vnx_price NUMERIC,
        timestamp_readable TIMESTAMP NOT NULL,
        collected_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (symbol, timestamp_readable)
    );
    """

    create_delayed_quotes_table = """
    CREATE TABLE IF NOT EXISTS delayed_quotes (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        delayed_price NUMERIC,
        delayed_time_readable TIMESTAMP NOT NULL,
        collected_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (symbol, delayed_time_readable)
    );
    """

    create_matched_quote_analysis_table = """
    CREATE TABLE IF NOT EXISTS matched_quote_analysis (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        vnx_price NUMERIC,
        vnx_time TIMESTAMP NOT NULL,
        delayed_price NUMERIC,
        delayed_time TIMESTAMP,
        time_gap_seconds NUMERIC,
        valid_match BOOLEAN,
        difference NUMERIC,
        percentage_error NUMERIC,
        absolute_percentage_error NUMERIC,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (symbol, vnx_time)
    );
    """

    create_quote_snapshot_audit_table = """
    CREATE TABLE IF NOT EXISTS quote_snapshot_audit (
        id SERIAL PRIMARY KEY,
        cycle_id TIMESTAMP NOT NULL,
        source TEXT NOT NULL,
        symbol TEXT NOT NULL,
        requested BOOLEAN NOT NULL,
        returned BOOLEAN NOT NULL,
        source_timestamp TIMESTAMP,
        collected_at TIMESTAMP,
        source_age_seconds NUMERIC,
        price NUMERIC,
        status TEXT NOT NULL,
        reason TEXT,
        batch_number INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (cycle_id, source, symbol)
    );
    """

    create_indexes = """
    CREATE INDEX IF NOT EXISTS idx_vnx_quotes_symbol_time
        ON vnx_quotes (symbol, timestamp_readable);

    CREATE INDEX IF NOT EXISTS idx_delayed_quotes_symbol_time
        ON delayed_quotes (symbol, delayed_time_readable);

    CREATE INDEX IF NOT EXISTS idx_matched_quote_symbol_time
        ON matched_quote_analysis (symbol, vnx_time);

    CREATE INDEX IF NOT EXISTS idx_quote_snapshot_audit_cycle_source
        ON quote_snapshot_audit (cycle_id DESC, source);

    CREATE INDEX IF NOT EXISTS idx_quote_snapshot_audit_symbol_source
        ON quote_snapshot_audit (symbol, source, cycle_id DESC);

    CREATE INDEX IF NOT EXISTS idx_quote_snapshot_audit_status
        ON quote_snapshot_audit (status, cycle_id DESC);
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(create_sp500_symbols_table)
            cursor.execute(create_vnx_quotes_table)
            cursor.execute(create_delayed_quotes_table)
            cursor.execute(create_matched_quote_analysis_table)
            cursor.execute(create_quote_snapshot_audit_table)
            cursor.execute(create_indexes)

        connection.commit()

    create_pipeline_health_table()

    print("Database tables and indexes created successfully.")
