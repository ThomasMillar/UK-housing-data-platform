import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from glob import glob

# Database connection string
engine = create_engine(
    "postgresql://housing_user:housing_password@localhost:5432/housing_db"
)

# Load only 2019 & 2020 files
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

    # Convert types
    df["transfer_date"] = pd.to_datetime(df["transfer_date"])
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # Drop null prices just in case
    df = df.dropna(subset=["price"])

    # Load in chunks
    df.to_sql(
        "price_paid",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000
    )

    print(f"Loaded {len(df)} rows")

print("All done!")