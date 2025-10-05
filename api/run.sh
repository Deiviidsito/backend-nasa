#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Iniciando CleanSky Los Ángeles API..."
echo "📍 Directorio: $(pwd)"
echo "🐍 Python: $(python3 --version)"

# Verificar que existe el dataset
if [ ! -f "../data/processed/airs_risk.nc" ]; then
    echo "❌ Error: No se encuentra el dataset airs_risk.nc"
    echo "💡 Ejecuta primero la Fase 2 para generar el dataset"
    exit 1
fi

echo "✅ Dataset encontrado"
echo "🌐 Iniciando servidor FastAPI..."

uvicorn main:app --host 0.0.0.0 --port 8001 --reload