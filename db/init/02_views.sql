-- Ensure transfer_date is DATE
-- ALTER TABLE transactions ALTER COLUMN transfer_date TYPE date USING transfer_date::date;

-- Ensure views resolve objects in the same schema as the table
CREATE SCHEMA IF NOT EXISTS housing;
SET search_path = housing, public;

CREATE OR REPLACE VIEW v_postcode_parts AS
SELECT
  transaction_id,
  price,
  transfer_date,
  postcode,
  split_part(postcode, ' ', 1) AS postcode_area,            -- e.g., "M25"
  regexp_replace(postcode, '(\\s\\d[[:alpha:]]{2})$', '') AS postcode_district, -- e.g., "M25 0"
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
FROM transactions;

-- Monthly averages (overall + by geography/type)
CREATE OR REPLACE VIEW monthly_avg_prices AS
SELECT
  date_trunc('month', transfer_date)::date AS month,
  county,
  district,
  property_type,
  old_new,
  duration,
  AVG(price) AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
  COUNT(*) AS transactions
FROM transactions
GROUP BY 1,2,3,4,5,6;

-- Yearly averages
CREATE OR REPLACE VIEW yearly_avg_prices AS
SELECT
  date_trunc('year', transfer_date)::date AS year,
  county,
  district,
  property_type,
  old_new,
  duration,
  AVG(price) AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
  COUNT(*) AS transactions
FROM transactions
GROUP BY 1,2,3,4,5,6;

-- Property type summary
CREATE OR REPLACE VIEW avg_by_property_type AS
SELECT
  property_type,
  AVG(price) AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
  COUNT(*) AS transactions
FROM transactions
GROUP BY 1;

-- New vs Old
CREATE OR REPLACE VIEW avg_by_old_new AS
SELECT
  old_new,
  AVG(price) AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
  COUNT(*) AS transactions
FROM transactions
GROUP BY 1;

-- Duration (Freehold vs Leasehold)
CREATE OR REPLACE VIEW avg_by_duration AS
SELECT
  duration,
  AVG(price) AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
  COUNT(*) AS transactions
FROM transactions
GROUP BY 1;

-- County rollup
CREATE OR REPLACE VIEW avg_by_county AS
SELECT
  county,
  AVG(price) AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
  COUNT(*) AS transactions
FROM transactions
GROUP BY 1;

-- District rollup
CREATE OR REPLACE VIEW avg_by_district AS
SELECT
  district,
  county,
  AVG(price) AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
  COUNT(*) AS transactions
FROM transactions
GROUP BY 1,2;
