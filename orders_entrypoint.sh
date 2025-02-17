#!/bin/bash
set -e

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting orders initialization..."

# Wait for PostgreSQL to start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking for PostgreSQL readiness..."
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Waiting for PostgreSQL..."
until pg_isready -h postgres -U postgres; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Waiting for PostgreSQL to be ready..."
  sleep 2
done
echo "[$(date '+%Y-%m-%d %H:%M:%S')] PostgreSQL is ready!"

# Run orders initialization
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting order insertion process..."
python -m src.utils.database.orders_insert
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Orders inserted successfully."

# Exit after completion
exit 0
