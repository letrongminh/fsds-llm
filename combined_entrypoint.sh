#!/bin/bash
set -e

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting initialization process..."

# Run orders initialization
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting order insertion process..."
python /app/src/utils/database/orders_insert.py
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Orders inserted successfully."

# Run FAQ processing
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting FAQ enrichment process..."
cd /app/src/utils/faq
echo "Running FAQ enrichment..."
python enrich_faq.py faq.json
echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAQ enrichment completed."

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Adding enriched FAQ to vector database..."
echo "y" | python add_document_to_pgvector.py
# echo "y" | python /app/src/utils/faq/add_document_to_pgvector.py
echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAQ added to vector database."

echo "[$(date '+%Y-%m-%d %H:%M:%S')] All initialization tasks completed successfully."

# Start Streamlit application
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Streamlit application..."
streamlit run /app/main.py

# Keep container running
tail -f /dev/null
