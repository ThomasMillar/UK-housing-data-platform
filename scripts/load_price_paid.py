import os
from glob import glob
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env vars from .env
load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "housing_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "housing_password")
DB_NAME = os.getenv("POSTGRES_DB", "housing_db")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")  # 'localhost' for host-run
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
TARGET_SCHEMA = os.getenv("TARGET_SCHEMA", "master_data")
TARGET_TABLE = "price_paid"

# Create engine
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Ensure schema exists
with engine.begin() as conn:
    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {TARGET_SCHEMA}"))

# Gather files
files = glob("data/raw/pp-2019-*.csv") + glob("data/raw/pp-2020-*.csv")
print(f"Found {len(files)} files")

# Load loop
for file in files:
    print(f"Processing {file}")
    df = pd.read_csv(file, header=None)

    df.columns = [
        "transaction_id", "price", "transfer_date", "postcode",
        "property_type", "old_new", "duration",
        "paon", "saon", "street", "locality",
        "town_city", "district", "county",
        "category_type", "record_status"
    ]

    # Types
    df["transfer_date"] = pd.to_datetime(df["transfer_date"], errors="coerce", utc=False).dt.date
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])

    # Write to schema
    df.to_sql(
        TARGET_TABLE,
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000,
        schema=TARGET_SCHEMA,
    )

    print(f"Loaded {len(df)} rows into {TARGET_SCHEMA}.{TARGET_TABLE}")

print("All done!")