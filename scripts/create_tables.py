import os
import sys
import logging
import psycopg2
from psycopg2 import sql
from contextlib import closing

# Load environment variables

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "housing_db")
DB_USER = os.getenv("POSTGRES_USER", "housing_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "housing_password")

SOURCE_SCHEMA = "master_data"
SOURCE_TABLE = "price_paid"

TARGET_SCHEMA = "housing_data"
TARGET_TABLE = "transactions"

LOAD_MODE = os.getenv("LOAD_MODE", "FULL_REFRESH").upper()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout
)


def main():
    with closing(psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )) as conn:

        conn.autocommit = False

        with conn.cursor() as cur:

# Ensure master_data exists

            cur.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name = %s
            """, (SOURCE_SCHEMA,))

            if cur.fetchone() is None:
                raise RuntimeError(
                    f"Source schema '{SOURCE_SCHEMA}' does not exist. "
                    "Load master data first using load_price_paid.py."
                )

# Create housing_data schema

            logging.info("Ensuring schema housing_data exists...")
            cur.execute(sql.SQL(
                "CREATE SCHEMA IF NOT EXISTS {}"
            ).format(sql.Identifier(TARGET_SCHEMA)))

# Create target table structure

            logging.info(f"Ensuring table {TARGET_SCHEMA}.{TARGET_TABLE} exists...")

            cur.execute(sql.SQL("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = {t_schema}
                          AND table_name   = {t_table}
                    ) THEN
                        EXECUTE format(
                            'CREATE TABLE %I.%I (LIKE %I.%I INCLUDING ALL)',
                            {t_schema}, {t_table},
                            {s_schema}, {s_table}
                        );
                    END IF;
                END$$;
            """).format(
                t_schema=sql.Literal(TARGET_SCHEMA),
                t_table=sql.Literal(TARGET_TABLE),
                s_schema=sql.Literal(SOURCE_SCHEMA),
                s_table=sql.Literal(SOURCE_TABLE)
            ))

# Load data

            if LOAD_MODE == "FULL_REFRESH":
                logging.info("Running FULL_REFRESH...")

                cur.execute(
                    sql.SQL("TRUNCATE {}.{}")
                    .format(sql.Identifier(TARGET_SCHEMA), sql.Identifier(TARGET_TABLE))
                )

                cur.execute(sql.SQL("""
                    INSERT INTO {}.{}
                    SELECT *
                    FROM {}.{}
                """).format(
                    sql.Identifier(TARGET_SCHEMA), sql.Identifier(TARGET_TABLE),
                    sql.Identifier(SOURCE_SCHEMA), sql.Identifier(SOURCE_TABLE),
                ))

            elif LOAD_MODE == "UPSERT":
                logging.info("Running UPSERT...")

                cur.execute(sql.SQL("""
                    INSERT INTO {t_schema}.{t_table}
                    SELECT *
                    FROM {s_schema}.{s_table}
                    ON CONFLICT (transaction_id)
                    DO NOTHING;
                """).format(
                    t_schema=sql.Identifier(TARGET_SCHEMA),
                    t_table=sql.Identifier(TARGET_TABLE),
                    s_schema=sql.Identifier(SOURCE_SCHEMA),
                    s_table=sql.Identifier(SOURCE_TABLE)
                ))

            else:
                raise ValueError(f"Invalid LOAD_MODE: {LOAD_MODE}")

            conn.commit()
            logging.info("Finished successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception("Execution failed: %s", e)
        sys.exit(1)