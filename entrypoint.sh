#!/bin/bash
set -e

echo "🚀 Starting container lifecycle..."

# 1. Mirror docs directory from the control plane host
echo "⏳ Fetching docs from control plane..."
wget -q -r -np -nH --cut-dirs=1 -R "index.html*" http://192.168.122.1/docs/

# 2. Run the data ingestion pipeline
echo "⏳ Running data ingestion..."
python ingest.py

# 3. Start the FastAPI server
echo "✅ Ingestion complete. Starting API gateway..."
exec uvicorn main:api --host 0.0.0.0 --port 8000
