import os
import re
import logging
import sys
from glob import glob
from contextlib import closing

import pandas as pd
import psycopg2

from psycopg2 import sql
from psycopg2.extras import execute_values

from dotenv import load_dotenv


# ENVIRONMENT

load_dotenv()


DB_USER = os.getenv(
    "POSTGRES_USER",
    "housing_user",
)

DB_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD",
    "housing_password",
)

DB_NAME = os.getenv(
    "POSTGRES_DB",
    "housing_db",
)

DB_HOST = os.getenv(
    "POSTGRES_HOST",
    "localhost",
)

DB_PORT = os.getenv(
    "POSTGRES_PORT",
    "5432",
)


START_YEAR = int(
    os.getenv(
        "START_YEAR",
        "2019",
    )
)


END_YEAR = int(
    os.getenv(
        "END_YEAR",
        "2025",
    )
)


SOURCE_SCHEMA = "master_data"
SOURCE_TABLE = "price_paid"


# DATASET COLUMNS

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


# LOGGING

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)


# FILE DISCOVERY

def get_input_files():
    """
    Find CSV files matching the configured year range.

    If both a complete file and part files exist for the
    same year, use the part files and ignore the complete file.
    """

    all_files = glob(
        "data/raw/*.csv"
    )


    files_by_year = {}


    for filepath in all_files:

        filename = os.path.basename(
            filepath
        )


        match = FILE_PATTERN.match(
            filename
        )

        if not match:
            continue


        year = int(
            match.group(1)
        )


        if year < START_YEAR or year > END_YEAR:
            continue


        is_part = "-part" in filename.lower()


        files_by_year.setdefault(
            year,
            [],
        ).append(
            {
                "path": filepath,
                "is_part": is_part,
            }
        )


    selected_files = []


    for year in range(
        START_YEAR,
        END_YEAR + 1,
    ):

        year_files = files_by_year.get(
            year,
            [],
        )


        if not year_files:

            logging.warning(
                "No CSV found for %s",
                year,
            )

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


        if part_files:

            selected_files.extend(
                sorted(part_files)
            )

        elif complete_files:

            selected_files.append(
                sorted(complete_files)[0]
            )


    return selected_files


# DATABASE SETUP

def ensure_source_table(cur):
    """
    Ensure the master_data schema and table exist.
    """

    cur.execute(
        sql.SQL(
            "CREATE SCHEMA IF NOT EXISTS {}"
        ).format(
            sql.Identifier(
                SOURCE_SCHEMA
            )
        )
    )


    cur.execute(
        """
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

            record_status CHAR(1)

        )
        """
    )


# UNIQUE TRANSACTION INDEX

def ensure_transaction_index(cur):
    """
    Ensure transaction_id can be used for idempotent upserts.

    This also removes accidental duplicate transaction IDs
    from older versions of the master table before creating
    the unique index.
    """

    cur.execute(
        """
        DELETE FROM master_data.price_paid a

        USING master_data.price_paid b

        WHERE a.ctid < b.ctid

        AND a.transaction_id = b.transaction_id
        """
    )


    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_price_paid_transaction_id

        ON master_data.price_paid(transaction_id)
        """
    )


# INSERT / UPDATE SQL

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

        record_status = EXCLUDED.record_status
"""


# LOAD A SINGLE FILE

def load_file(cur, filepath):

    logging.info(
        "Processing %s",
        filepath,
    )


    total_rows = 0


    for chunk in pd.read_csv(
        filepath,
        header=None,
        names=COLUMNS,
        chunksize=50_000,
        low_memory=False,
    ):

        # CLEAN DATA

        chunk["transfer_date"] = (
            pd.to_datetime(
                chunk["transfer_date"],
                errors="coerce",
            )
            .dt.date
        )


        chunk["price"] = pd.to_numeric(
            chunk["price"],
            errors="coerce",
        )


        chunk = chunk.dropna(
            subset=[
                "transaction_id",
                "price",
            ]
        )


        # Remove accidental duplicate transaction IDs
        # within the same CSV chunk.
        chunk = chunk.drop_duplicates(
            subset=[
                "transaction_id"
            ],
            keep="last",
        )


        if chunk.empty:
            continue


        # CONVERT NaN / NaT → None

        chunk = chunk.astype(
            object
        ).where(
            pd.notna(chunk),
            None,
        )


        records = list(
            chunk.itertuples(
                index=False,
                name=None,
            )
        )


        # UPSERT

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
        filepath,
        total_rows,
    )


# MAIN

def main():

    logging.info(
        "Loading Price Paid Data "
        "from %s to %s",
        START_YEAR,
        END_YEAR,
    )


    files = get_input_files()


    if not files:

        raise RuntimeError(
            "No matching CSV files were found. "
            "Check START_YEAR / END_YEAR and "
            "data/raw."
        )


    logging.info(
        "Found %s input files.",
        len(files),
    )


    connection_string = (
        f"host={DB_HOST} "
        f"port={DB_PORT} "
        f"dbname={DB_NAME} "
        f"user={DB_USER} "
        f"password={DB_PASSWORD}"
    )


    with closing(
        psycopg2.connect(
            connection_string
        )
    ) as conn:

        conn.autocommit = False


        try:

            with conn.cursor() as cur:

                ensure_source_table(
                    cur
                )


                ensure_transaction_index(
                    cur
                )


                for filepath in files:

                    load_file(
                        cur,
                        filepath,
                    )


                conn.commit()


                logging.info(
                    "All files loaded successfully."
                )


        except Exception:

            conn.rollback()

            logging.exception(
                "Load failed. Transaction rolled back."
            )

            raise


# RUN

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        logging.exception(
            "Execution failed: %s",
            exc,
        )

        sys.exit(1)