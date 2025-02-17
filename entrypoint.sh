#!/bin/bash
set -e

echo "Starting FAQ processing..."

# Chờ PostgreSQL khởi động
echo "Waiting for PostgreSQL..."
until pg_isready -h postgres -U postgres; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done
echo "PostgreSQL is ready!"

# Chạy enrichment
cd /app/src/utils/faq
echo "Running FAQ enrichment..."
python enrich_faq.py faq.json

# Thêm vào vector DB
echo "Adding to vector database..."
echo "y" | python add_document_to_pgvector.py

echo "FAQ processing completed successfully!"

# Keep container running
tail -f /dev/null
