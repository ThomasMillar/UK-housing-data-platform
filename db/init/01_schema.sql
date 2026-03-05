-- Create new schema to seperate Master data
CREATE SCHEMA IF NOT EXISTS housing;
SET search_path = housing, public;

CREATE TABLE IF NOT EXISTS transactions (
    -- Identifiers
    transaction_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Facts
    price               NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    transfer_date       DATE NOT NULL,

    -- Geography
    postcode            TEXT,                 -- full postcode (e.g., "M25 0AA")
    property_type       TEXT,                 -- e.g., 'D','S','T','F'
    old_new             TEXT,                 -- e.g., 'Y' (new) / 'N' (old)
    duration            TEXT,                 -- e.g., 'F' (freehold) / 'L' (leasehold)

    -- Address components
    paon                TEXT,                 -- Primary Addressable Object Name (e.g., house number or name)
    saon                TEXT,                 -- Secondary Addressable Object Name (e.g., Flat 2)
    street              TEXT,
    locality            TEXT,
    town_city           TEXT,
    district            TEXT,
    county              TEXT,

    -- Other Data
    category_type       TEXT,                 -- e.g., 'A','B' etc. (HMLR categories)
    record_status       TEXT,                 -- e.g., 'A','C','D' etc.
    
    -- Raw line storage
    source_row          JSONB
);

-- Indexes for common filters and joins

-- Time-based queries (trends, monthly averages)
CREATE INDEX IF NOT EXISTS idx_transactions_transfer_date
    ON transactions (transfer_date);

-- Geography filters
CREATE INDEX IF NOT EXISTS idx_transactions_county
    ON transactions (county);

CREATE INDEX IF NOT EXISTS idx_transactions_district
    ON transactions (district);

CREATE INDEX IF NOT EXISTS idx_transactions_town_city
    ON transactions (town_city);

-- Postcode lookups; text_pattern_ops helps LIKE/ILIKE prefix searches
CREATE INDEX IF NOT EXISTS idx_transactions_postcode
    ON transactions (postcode text_pattern_ops);

-- By property characteristics
CREATE INDEX IF NOT EXISTS idx_transactions_property_type
    ON transactions (property_type);

CREATE INDEX IF NOT EXISTS idx_transactions_old_new
    ON transactions (old_new);

CREATE INDEX IF NOT EXISTS idx_transactions_duration
    ON transactions (duration);

-- Composite index useful for regional time-series charts
CREATE INDEX IF NOT EXISTS idx_transactions_county_date
    ON transactions (county, transfer_date);