import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="housing_db",
    user="housing_user",
    password="housing_password",
    port=5432
)

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS price_paid (
    transaction_id TEXT PRIMARY KEY,
    price INTEGER,
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
);
""")

conn.commit()
cur.close()
conn.close()

print("Table created successfully!")