#!/bin/bash
# Exit immediately if any command fails
set -e

echo "🚀 Starting container lifecycle..."

# 1. Run the data ingestion pipeline
echo "⏳ Running data ingestion..."
python ingest.py

# 2. Start the FastAPI server
echo "✅ Ingestion complete. Starting API gateway..."
# exec replaces the shell process with the uvicorn process, 
# ensuring it receives OS signals (like SIGTERM for graceful shutdown) correctly.
exec uvicorn main:api --host 0.0.0.0 --port 8000