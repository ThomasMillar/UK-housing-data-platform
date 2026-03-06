import os
from glob import glob
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "housing_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "housing_password")
DB_NAME = os.getenv("POSTGRES_DB", "housing_db")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Load only 2019 & 2020
files = glob("data/raw/pp-2019-*.csv") + glob("data/raw/pp-2020-*.csv")
print(f"Found {len(files)} files")

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
    df["transfer_date"] = pd.to_datetime(df["transfer_date"], errors="coerce").dt.date
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])

# Creates master_data Schema
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS master_data"))

# Write into master_data
    df.to_sql(
        "price_paid",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000,
        schema="master_data",
    )
    print(f"Loaded {len(df)} rows")
print("All done!")