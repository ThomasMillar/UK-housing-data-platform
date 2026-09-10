import os
import sys
import logging

from contextlib import closing

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql


load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "housing_db")
DB_USER = os.getenv("POSTGRES_USER", "housing_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "housing_password")

SOURCE_SCHEMA = "master_data"
SOURCE_TABLE = "price_paid"

TARGET_SCHEMA = "housing_data"
TARGET_TABLE = "transactions"

LOAD_MODE = os.getenv("LOAD_MODE", "UPSERT").upper()

COLUMNS = [
    "transaction_id",
    "price",
    "transfer_date",
    "postcode",
    "property_type",
    "old_new",
    "duration",
    "paon",
    "saon",
    "street",
    "locality",
    "town_city",
    "district",
    "county",
    "category_type",
    "record_status",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)


def ensure_source_exists(cur):
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
        )
        """,
        (SOURCE_SCHEMA, SOURCE_TABLE),
    )

    if not cur.fetchone()[0]:
        raise RuntimeError(
            "master_data.price_paid does not exist. "
            "Run load_price_paid.py first."
        )


def ensure_target_table(cur):
    logging.info("Ensuring housing_data.transactions exists...")

    cur.execute(
        sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
            sql.Identifier(TARGET_SCHEMA)
        )
    )

    # Keep the curated table limited to the dashboard-facing columns.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS housing_data.transactions (
            transaction_id TEXT PRIMARY KEY,
            price BIGINT,
            transfer_date DATE,
            postcode TEXT,
            property_type CHAR(1),
            old_new CHAR(1),
            duration CHAR(1),
            paon TEXT,
            saon TEXT,
            street TEXT,
            locality TEXT,
            town_city TEXT,
            district TEXT,
            county TEXT,
            category_type CHAR(1),
            record_status CHAR(1)
        )
    """)

    # Older versions may have a unique index rather than a primary key.
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_transactions_transaction_id
        ON housing_data.transactions(transaction_id)
    """)


def ensure_pipeline_state(cur):
    """Store the timestamp of the last successful curated-table sync."""

    cur.execute("""
        CREATE TABLE IF NOT EXISTS housing_data.pipeline_state (
            process_name TEXT PRIMARY KEY,
            last_synced_at TIMESTAMPTZ NOT NULL
        )
    """)


def get_last_sync(cur):
    cur.execute("""
        SELECT last_synced_at
        FROM housing_data.pipeline_state
        WHERE process_name = 'transactions_sync'
    """)

    result = cur.fetchone()
    return result[0] if result else None


def set_last_sync(cur, timestamp):
    cur.execute(
        """
        INSERT INTO housing_data.pipeline_state (
            process_name,
            last_synced_at
        )
        VALUES ('transactions_sync', %s)

        ON CONFLICT (process_name)
        DO UPDATE SET
            last_synced_at = EXCLUDED.last_synced_at
        """,
        (timestamp,),
    )


def initialise_sync_state(cur):
    """Set the first sync point without unnecessarily reloading existing data."""

    cur.execute("SELECT COUNT(*) FROM housing_data.transactions")
    target_rows = cur.fetchone()[0]

    if target_rows == 0:
        logging.info("Target table is empty. Initial full sync required.")
        return None

    # Existing target data predates pipeline_state, so use the newest master timestamp.
    cur.execute("SELECT MAX(updated_at) FROM master_data.price_paid")
    baseline = cur.fetchone()[0]

    if baseline is not None:
        set_last_sync(cur, baseline)
        logging.info(
            "Initialised sync state for existing %s target rows.",
            target_rows,
        )

    return baseline


def full_refresh(cur):
    logging.info("Running FULL_REFRESH...")

    cur.execute("""
        TRUNCATE TABLE housing_data.transactions
    """)

    cur.execute("""
        INSERT INTO housing_data.transactions (
            transaction_id,
            price,
            transfer_date,
            postcode,
            property_type,
            old_new,
            duration,
            paon,
            saon,
            street,
            locality,
            town_city,
            district,
            county,
            category_type,
            record_status
        )
        SELECT
            transaction_id,
            price,
            transfer_date,
            postcode,
            property_type,
            old_new,
            duration,
            paon,
            saon,
            street,
            locality,
            town_city,
            district,
            county,
            category_type,
            record_status
        FROM master_data.price_paid
    """)

    rows_loaded = cur.rowcount

    cur.execute("SELECT MAX(updated_at) FROM master_data.price_paid")
    latest_update = cur.fetchone()[0]

    if latest_update is not None:
        set_last_sync(cur, latest_update)

    logging.info("Loaded %s transactions.", rows_loaded)


def incremental_sync(cur):
    last_synced_at = get_last_sync(cur)

    if last_synced_at is None:
        last_synced_at = initialise_sync_state(cur)

    # Empty target on a fresh database needs every master row.
    if last_synced_at is None:
        full_refresh(cur)
        return

    cur.execute("SELECT NOW()")
    sync_cutoff = cur.fetchone()[0]

    logging.info(
        "Syncing changes after %s...",
        last_synced_at,
    )

    cur.execute(
        """
        INSERT INTO housing_data.transactions (
            transaction_id,
            price,
            transfer_date,
            postcode,
            property_type,
            old_new,
            duration,
            paon,
            saon,
            street,
            locality,
            town_city,
            district,
            county,
            category_type,
            record_status
        )
        SELECT
            transaction_id,
            price,
            transfer_date,
            postcode,
            property_type,
            old_new,
            duration,
            paon,
            saon,
            street,
            locality,
            town_city,
            district,
            county,
            category_type,
            record_status
        FROM master_data.price_paid
        WHERE updated_at > %s
          AND updated_at <= %s

        ON CONFLICT (transaction_id)
        DO UPDATE SET
            price = EXCLUDED.price,
            transfer_date = EXCLUDED.transfer_date,
            postcode = EXCLUDED.postcode,
            property_type = EXCLUDED.property_type,
            old_new = EXCLUDED.old_new,
            duration = EXCLUDED.duration,
            paon = EXCLUDED.paon,
            saon = EXCLUDED.saon,
            street = EXCLUDED.street,
            locality = EXCLUDED.locality,
            town_city = EXCLUDED.town_city,
            district = EXCLUDED.district,
            county = EXCLUDED.county,
            category_type = EXCLUDED.category_type,
            record_status = EXCLUDED.record_status
        """,
        (last_synced_at, sync_cutoff),
    )

    rows_synced = cur.rowcount

    # Only advance the checkpoint after the SQL above succeeds.
    set_last_sync(cur, sync_cutoff)

    logging.info("Synced %s changed transactions.", rows_synced)


def main():
    connection_string = (
        f"host={DB_HOST} "
        f"port={DB_PORT} "
        f"dbname={DB_NAME} "
        f"user={DB_USER} "
        f"password={DB_PASSWORD}"
    )

    with closing(psycopg2.connect(connection_string)) as conn:
        conn.autocommit = False

        try:
            with conn.cursor() as cur:
                ensure_source_exists(cur)
                ensure_target_table(cur)
                ensure_pipeline_state(cur)

                if LOAD_MODE == "FULL_REFRESH":
                    full_refresh(cur)
                elif LOAD_MODE == "UPSERT":
                    logging.info("Running incremental UPSERT...")
                    incremental_sync(cur)
                else:
                    raise ValueError(f"Invalid LOAD_MODE: {LOAD_MODE}")

                conn.commit()
                logging.info("Finished successfully.")

        except Exception:
            conn.rollback()
            logging.exception("Sync failed. Transaction rolled back.")
            raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("Execution failed: %s", exc)
        sys.exit(1)