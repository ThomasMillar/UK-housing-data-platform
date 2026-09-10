#!/usr/bin/env bash

set -euo pipefail


# DATABASE CONFIG

export PGPASSWORD="${POSTGRES_PASSWORD:-}"

echo "[boot] Starting UK Housing Data Platform..."
echo "[boot] Configured data range: ${START_YEAR:-2019} to ${END_YEAR:-2025}"


# WAIT FOR POSTGRES

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


# INSTALL PYTHON DEPENDENCIES

echo "[boot] Installing Python dependencies..."

pip install \
    --no-cache-dir \
    -r requirements.txt


# CHECK MASTER DATA

echo "[boot] Checking master_data.price_paid..."

TABLE_EXISTS=$(psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -tAc "
        SELECT to_regclass('master_data.price_paid') IS NOT NULL;
    "
)


if [ "${TABLE_EXISTS}" = "t" ]; then

    ROWCOUNT=$(psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        -tAc "
            SELECT COUNT(*)
            FROM master_data.price_paid;
        "
    )

else

    ROWCOUNT=0

fi


# INITIAL MASTER DATA LOAD

if [ "${ROWCOUNT}" -eq 0 ]; then

    echo "[boot] Master data is empty."
    echo "[boot] Running initial Price Paid Data load..."

    python scripts/load_price_paid.py

    echo "[boot] Initial master data load complete."

else

    echo "[boot] Master data already contains ${ROWCOUNT} rows."
    echo "[boot] Skipping full CSV reload."

fi


# SYNC CURATED TRANSACTIONS TABLE

echo "[boot] Syncing housing_data.transactions..."

LOAD_MODE="${LOAD_MODE:-UPSERT}" \
python scripts/create_tables.py

echo "[boot] housing_data.transactions sync complete."


# REFRESH MATERIALIZED VIEWS

echo "[boot] Refreshing materialized views..."

psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -v ON_ERROR_STOP=1 \
    -c "SELECT housing_data.refresh_all_materialized_views(TRUE);"

echo "[boot] Materialized views refreshed."


# COMPLETE

echo "[boot] Pipeline complete."