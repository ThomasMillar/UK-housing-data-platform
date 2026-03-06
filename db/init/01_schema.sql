CREATE SCHEMA IF NOT EXISTS housing_data;

CREATE TABLE IF NOT EXISTS housing_data.transactions (
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