set -euo pipefail

export PGPASSWORD="${POSTGRES_PASSWORD:-}"

echo "[boot] Waiting for Postgres to be ready..."
until pg_isready -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; do
  sleep 2
done
echo "[boot] Postgres is ready."

echo "[boot] Checking if master data exists..."

PSQL_URI="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

# Checks if table exists
EXISTS=$(psql "${PSQL_URI}" -Atqc "
  SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='master_data' AND table_name='price_paid'
  );
")
EXISTS="${EXISTS:-f}"

ROWCOUNT=0
if [ "$EXISTS" = "t" ]; then
  ROWCOUNT=$(psql "${PSQL_URI}" -Atqc "SELECT COUNT(*) FROM master_data.price_paid" || echo "0")
fi
echo "[boot] master_data.price_paid exists: ${EXISTS}, rows: ${ROWCOUNT}"

# Install Python libraries
pip install --no-cache-dir -r requirements.txt

# Loads master data (only if missing/empty)
if [ "$EXISTS" != "t" ] || [ "$ROWCOUNT" = "0" ]; then
  echo "[boot] Loading master data via scripts/load_price_paid.py ..."
  POSTGRES_HOST="${POSTGRES_HOST}" POSTGRES_PORT="${POSTGRES_PORT}" \
  POSTGRES_DB="${POSTGRES_DB}" POSTGRES_USER="${POSTGRES_USER}" \
  POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  python scripts/load_price_paid.py
else
  echo "[boot] Master data already present. Skipping load."
fi

# Sync curated tables
echo "[boot] Sync housing_data.transactions via scripts/create_tables.py ..."
LOAD_MODE="${LOAD_MODE:-UPSERT}" \
POSTGRES_HOST="${POSTGRES_HOST}" POSTGRES_PORT="${POSTGRES_PORT}" \
POSTGRES_DB="${POSTGRES_DB}" POSTGRES_USER="${POSTGRES_USER}" \
POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
python scripts/create_tables.py

# Refresh views
echo "[boot] Refreshing materialized views..."
psql "${PSQL_URI}" -v ON_ERROR_STOP=1 -c "SELECT housing_data.refresh_all_materialized_views(TRUE);"

echo "[boot] Done."