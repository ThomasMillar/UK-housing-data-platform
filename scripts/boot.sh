#!/usr/bin/env bash

set -euo pipefail

export PGPASSWORD="${POSTGRES_PASSWORD:-}"

echo "[boot] Starting UK Housing Data Platform..."
echo "[boot] Configured data range: ${START_YEAR:-2019} to ${END_YEAR:-2025}"

echo "[boot] Waiting for Postgres to be ready..."

until pg_isready \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    >/dev/null 2>&1
do
    sleep 2
done

echo "[boot] Postgres is ready."

echo "[boot] Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Loader now skips files already recorded in master_data.ingestion_log.
echo "[boot] Checking for new Price Paid Data..."
python scripts/load_price_paid.py
echo "[boot] Price Paid Data check complete."

echo "[boot] Syncing housing_data.transactions..."
LOAD_MODE="${LOAD_MODE:-UPSERT}" python scripts/create_tables.py
echo "[boot] housing_data.transactions sync complete."

echo "[boot] Refreshing materialized views..."

psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -v ON_ERROR_STOP=1 \
    -c "SELECT housing_data.refresh_all_materialized_views(TRUE);"

echo "[boot] Materialized views refreshed."
echo "[boot] Pipeline complete."