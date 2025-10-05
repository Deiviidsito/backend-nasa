#!/bin/bash

# Railway startup script for CleanSky North America API

echo "🚀 Starting CleanSky North America API..."
echo "Environment: ${RAILWAY_ENVIRONMENT:-development}"
echo "Port: ${PORT:-8000}"

# Create necessary directories
mkdir -p data/processed data/zarr_store logs

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}