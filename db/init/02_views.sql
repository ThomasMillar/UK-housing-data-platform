SET client_min_messages TO WARNING;

-- Ensure schema exists
CREATE SCHEMA IF NOT EXISTS housing_data;

-- Creating Indexes

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'housing_data' AND tablename = 'transactions'
      AND indexname = 'ix_transactions_transfer_date'
  ) THEN
    EXECUTE 'CREATE INDEX ix_transactions_transfer_date ON housing_data.transactions (transfer_date)';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'housing_data' AND tablename = 'transactions'
      AND indexname = 'ix_transactions_county'
  ) THEN
    EXECUTE 'CREATE INDEX ix_transactions_county ON housing_data.transactions (county)';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'housing_data' AND tablename = 'transactions'
      AND indexname = 'ix_transactions_district'
  ) THEN
    EXECUTE 'CREATE INDEX ix_transactions_district ON housing_data.transactions (district)';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'housing_data' AND tablename = 'transactions'
      AND indexname = 'ix_transactions_town_city'
  ) THEN
    EXECUTE 'CREATE INDEX ix_transactions_town_city ON housing_data.transactions (town_city)';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'housing_data' AND tablename = 'transactions'
      AND indexname = 'ix_transactions_property_type'
  ) THEN
    EXECUTE 'CREATE INDEX ix_transactions_property_type ON housing_data.transactions (property_type)';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'housing_data' AND tablename = 'transactions'
      AND indexname = 'ix_transactions_date_county'
  ) THEN
    EXECUTE 'CREATE INDEX ix_transactions_date_county ON housing_data.transactions (transfer_date, county)';
  END IF;
END$$;

-- Monthly Price Summary view
CREATE MATERIALIZED VIEW IF NOT EXISTS housing_data.mv_monthly_prices AS
SELECT
  date_trunc('month', transfer_date)::date AS month,
  COUNT(*)::BIGINT                         AS n_transactions,
  AVG(price)::NUMERIC                      AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price
FROM housing_data.transactions
WHERE record_status <> 'D'
GROUP BY 1
ORDER BY 1;

-- Concurrent refresh Index
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='housing_data'
      AND indexname='ux_mv_monthly_prices_month'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX ux_mv_monthly_prices_month ON housing_data.mv_monthly_prices (month)';
  END IF;
END$$;

-- County Summary View
CREATE MATERIALIZED VIEW IF NOT EXISTS housing_data.mv_county_summary AS
SELECT
  county,
  COUNT(*)::BIGINT AS n_transactions,
  AVG(price)::NUMERIC AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price
FROM housing_data.transactions
WHERE record_status <> 'D' AND county IS NOT NULL
GROUP BY county;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='housing_data'
      AND indexname='ux_mv_county_summary'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX ux_mv_county_summary ON housing_data.mv_county_summary (county)';
  END IF;
END$$;

-- District Summary View
CREATE MATERIALIZED VIEW IF NOT EXISTS housing_data.mv_district_summary AS
SELECT
  district,
  COUNT(*)::BIGINT AS n_transactions,
  AVG(price)::NUMERIC AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price
FROM housing_data.transactions
WHERE record_status <> 'D' AND district IS NOT NULL
GROUP BY district;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='housing_data'
      AND indexname='ux_mv_district_summary'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX ux_mv_district_summary ON housing_data.mv_district_summary (district)';
  END IF;
END$$;

-- Town/City Summary View
CREATE MATERIALIZED VIEW IF NOT EXISTS housing_data.mv_town_summary AS
SELECT
  town_city,
  COUNT(*)::BIGINT AS n_transactions,
  AVG(price)::NUMERIC AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price
FROM housing_data.transactions
WHERE record_status <> 'D' AND town_city IS NOT NULL
GROUP BY town_city;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='housing_data'
      AND indexname='ux_mv_town_summary'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX ux_mv_town_summary ON housing_data.mv_town_summary (town_city)';
  END IF;
END$$;

-- Property Type  View
CREATE MATERIALIZED VIEW IF NOT EXISTS housing_data.mv_property_mix AS
SELECT
  property_type,
  COUNT(*)::BIGINT AS n_transactions,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price
FROM housing_data.transactions
WHERE record_status <> 'D' AND property_type IS NOT NULL
GROUP BY property_type;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='housing_data'
      AND indexname='ux_mv_property_mix'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX ux_mv_property_mix ON housing_data.mv_property_mix (property_type)';
  END IF;
END$$;

-- Monthly Affordability Percentiles View
CREATE MATERIALIZED VIEW IF NOT EXISTS housing_data.mv_monthly_affordability AS
SELECT
  date_trunc('month', transfer_date)::date AS month,
  PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY price) AS p10,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price) AS p25,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price) AS p50,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price) AS p75,
  PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY price) AS p90
FROM housing_data.transactions
WHERE record_status <> 'D'
GROUP BY 1
ORDER BY 1;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='housing_data'
      AND indexname='ux_mv_monthly_affordability'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX ux_mv_monthly_affordability ON housing_data.mv_monthly_affordability (month)';
  END IF;
END$$;

-- Regular Views

CREATE OR REPLACE VIEW housing_data.v_monthly_prices AS
SELECT * FROM housing_data.mv_monthly_prices;

CREATE OR REPLACE VIEW housing_data.v_county_summary AS
SELECT * FROM housing_data.mv_county_summary;

CREATE OR REPLACE VIEW housing_data.v_district_summary AS
SELECT * FROM housing_data.mv_district_summary;

CREATE OR REPLACE VIEW housing_data.v_town_summary AS
SELECT * FROM housing_data.mv_town_summary;

CREATE OR REPLACE VIEW housing_data.v_property_mix AS
SELECT * FROM housing_data.mv_property_mix;

CREATE OR REPLACE VIEW housing_data.v_monthly_affordability AS
SELECT * FROM housing_data.mv_monthly_affordability;

-- Refresh all MVs
CREATE OR REPLACE FUNCTION housing_data.refresh_all_materialized_views(p_concurrently BOOLEAN DEFAULT TRUE)
RETURNS void LANGUAGE plpgsql AS
$$
BEGIN
  IF p_concurrently THEN
    -- Requires unique indexes
    REFRESH MATERIALIZED VIEW CONCURRENTLY housing_data.mv_monthly_prices;
    REFRESH MATERIALIZED VIEW CONCURRENTLY housing_data.mv_county_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY housing_data.mv_district_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY housing_data.mv_town_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY housing_data.mv_property_mix;
    REFRESH MATERIALIZED VIEW CONCURRENTLY housing_data.mv_monthly_affordability;
  ELSE
    REFRESH MATERIALIZED VIEW housing_data.mv_monthly_prices;
    REFRESH MATERIALIZED VIEW housing_data.mv_county_summary;
    REFRESH MATERIALIZED VIEW housing_data.mv_district_summary;
    REFRESH MATERIALIZED VIEW housing_data.mv_town_summary;
    REFRESH MATERIALIZED VIEW housing_data.mv_property_mix;
    REFRESH MATERIALIZED VIEW housing_data.mv_monthly_affordability;
  END IF;
END;
$$;

-- First-time populate
SELECT housing_data.refresh_all_materialized_views(TRUE);