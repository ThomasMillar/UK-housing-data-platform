import os
import re
import logging
import sys

from contextlib import closing
from glob import glob

import pandas as pd
import psycopg2

from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import execute_values


load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "housing_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "housing_password")
DB_NAME = os.getenv("POSTGRES_DB", "housing_db")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

START_YEAR = int(os.getenv("START_YEAR", "2019"))
END_YEAR = int(os.getenv("END_YEAR", "2025"))

SOURCE_SCHEMA = "master_data"
SOURCE_TABLE = "price_paid"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

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

FILE_PATTERN = re.compile(
    r"pp-(\d{4})(?:-part\d+)?\.csv$",
    re.IGNORECASE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)


if START_YEAR > END_YEAR:
    raise ValueError(
        f"START_YEAR ({START_YEAR}) cannot be greater than END_YEAR ({END_YEAR})."
    )


def get_input_files():
    """Find Price Paid CSV files within the configured year range."""

    all_files = glob(os.path.join(RAW_DIR, "*.csv"))
    files_by_year = {}

    for filepath in all_files:
        filename = os.path.basename(filepath)
        match = FILE_PATTERN.match(filename)

        if not match:
            continue

        year = int(match.group(1))

        if not START_YEAR <= year <= END_YEAR:
            continue

        files_by_year.setdefault(year, []).append({
            "path": filepath,
            "is_part": "-part" in filename.lower(),
        })

    selected_files = []

    for year in range(START_YEAR, END_YEAR + 1):
        year_files = files_by_year.get(year, [])

        if not year_files:
            logging.warning("No CSV found for %s", year)
            continue

        part_files = [
            item["path"]
            for item in year_files
            if item["is_part"]
        ]

        complete_files = [
            item["path"]
            for item in year_files
            if not item["is_part"]
        ]

        # Prefer part files when both formats exist.
        if part_files:
            selected_files.extend(sorted(part_files))
        elif complete_files:
            selected_files.append(sorted(complete_files)[0])

    return selected_files


def ensure_source_table(cur):
    """Create the master source table when required."""

    cur.execute(
        sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
            sql.Identifier(SOURCE_SCHEMA)
        )
    )

    cur.execute("""
        CREATE TABLE IF NOT EXISTS master_data.price_paid (
            transaction_id TEXT NOT NULL,
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
            record_status CHAR(1),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Adds the column safely to databases created before updated_at existed.
    cur.execute("""
        ALTER TABLE master_data.price_paid
        ADD COLUMN IF NOT EXISTS updated_at
        TIMESTAMPTZ NOT NULL DEFAULT NOW()
    """)


def ensure_transaction_index(cur):
    """Ensure transaction_id can be used for upserts."""

    cur.execute("""
        SELECT to_regclass(
            'master_data.ux_price_paid_transaction_id'
        )
    """)

    if cur.fetchone()[0]:
        return

    # Only run the duplicate cleanup when the unique index does not exist.
    logging.info("Creating unique transaction index...")

    cur.execute("""
        DELETE FROM master_data.price_paid a
        USING master_data.price_paid b
        WHERE a.ctid < b.ctid
          AND a.transaction_id = b.transaction_id
    """)

    cur.execute("""
        CREATE UNIQUE INDEX ux_price_paid_transaction_id
        ON master_data.price_paid(transaction_id)
    """)


def ensure_ingestion_log(cur):
    """Track which CSV files have already been processed."""

    cur.execute("""
        CREATE TABLE IF NOT EXISTS master_data.ingestion_log (
            filename TEXT PRIMARY KEY,
            rows_loaded BIGINT,
            loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def already_processed(cur, filename):
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM master_data.ingestion_log
            WHERE filename = %s
        )
        """,
        (filename,),
    )

    return cur.fetchone()[0]


def mark_processed(cur, filename, rows_loaded):
    cur.execute(
        """
        INSERT INTO master_data.ingestion_log (
            filename,
            rows_loaded,
            loaded_at
        )
        VALUES (%s, %s, NOW())

        ON CONFLICT (filename)
        DO UPDATE SET
            rows_loaded = EXCLUDED.rows_loaded,
            loaded_at = EXCLUDED.loaded_at
        """,
        (filename, rows_loaded),
    )


UPSERT_SQL = """
    INSERT INTO master_data.price_paid (
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
    VALUES %s

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
        record_status = EXCLUDED.record_status,
        updated_at = NOW()
"""


def load_file(cur, filepath):
    logging.info("Processing %s", os.path.basename(filepath))
    total_rows = 0

    for chunk in pd.read_csv(
        filepath,
        header=None,
        names=COLUMNS,
        chunksize=50_000,
        low_memory=False,
    ):
        chunk["transfer_date"] = pd.to_datetime(
            chunk["transfer_date"],
            errors="coerce",
        ).dt.date

        chunk["price"] = pd.to_numeric(
            chunk["price"],
            errors="coerce",
        )

        chunk = chunk.dropna(subset=["transaction_id", "price"])

        # Prevent duplicate IDs in the same CSV chunk.
        chunk = chunk.drop_duplicates(
            subset=["transaction_id"],
            keep="last",
        )

        if chunk.empty:
            continue

        # psycopg2 expects None instead of pandas NaN/NaT.
        chunk = chunk.astype(object).where(pd.notna(chunk), None)
        records = list(chunk.itertuples(index=False, name=None))

        execute_values(
            cur,
            UPSERT_SQL,
            records,
            page_size=5_000,
        )

        total_rows += len(records)

        logging.info(
            "Processed %s rows from %s",
            len(records),
            os.path.basename(filepath),
        )

    logging.info(
        "Finished %s — %s rows processed.",
        os.path.basename(filepath),
        total_rows,
    )

    return total_rows


def main():
    logging.info(
        "Checking Price Paid Data from %s to %s",
        START_YEAR,
        END_YEAR,
    )

    files = get_input_files()

    if not files:
        raise RuntimeError(
            "No matching CSV files were found. "
            "Check START_YEAR / END_YEAR and data/raw."
        )

    logging.info("Found %s input files.", len(files))

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
                ensure_source_table(cur)
                ensure_transaction_index(cur)
                ensure_ingestion_log(cur)
                conn.commit()

                new_files = 0

                for filepath in files:
                    filename = os.path.basename(filepath)

                    if already_processed(cur, filename):
                        logging.info(
                            "Skipping already processed file: %s",
                            filename,
                        )
                        continue

                    rows_loaded = load_file(cur, filepath)
                    mark_processed(cur, filename, rows_loaded)

                    # Keep each completed file as a separate successful transaction.
                    conn.commit()
                    new_files += 1

                if new_files == 0:
                    logging.info("No new files to process.")
                else:
                    logging.info(
                        "Loaded %s new file(s) successfully.",
                        new_files,
                    )

        except Exception:
            conn.rollback()
            logging.exception("Load failed. Current file rolled back.")
            raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("Execution failed: %s", exc)
        sys.exit(1)