#!/bin/bash
# Script de ejecución rápida para CleanSky Multi-Ciudad
# Configura y ejecuta el sistema completo optimizado

set -e

echo "🚀 CleanSky Multi-Ciudad - Configuración y Ejecución"
echo "=================================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de logging
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Configuración por defecto
ENVIRONMENT="development"
CITIES=""
SKIP_ETL=false
SAMPLE_DATA=false
RUN_API=true
PORT=8000

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --cities)
            CITIES="$2"
            shift 2
            ;;
        --skip-etl)
            SKIP_ETL=true
            shift
            ;;
        --sample-data)
            SAMPLE_DATA=true
            shift
            ;;
        --skip-api)
            RUN_API=false
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --help)
            echo "Uso: $0 [opciones]"
            echo ""
            echo "Opciones:"
            echo "  --environment ENV     Entorno (development|production_sqlite|production_postgresql)"
            echo "  --cities CITIES       Ciudades específicas (separadas por coma)"
            echo "  --skip-etl           Omitir ejecución de ETL"
            echo "  --sample-data        Usar datos de muestra"
            echo "  --skip-api           No ejecutar API después de configuración"
            echo "  --port PORT          Puerto para API (default: 8000)"
            echo "  --help               Mostrar esta ayuda"
            exit 0
            ;;
        *)
            log_error "Opción desconocida: $1"
            exit 1
            ;;
    esac
done

log_info "Configuración:"
log_info "  Entorno: $ENVIRONMENT"
log_info "  Puerto: $PORT"
log_info "  Ciudades: ${CITIES:-'todas'}"
log_info "  Ejecutar ETL: $([ "$SKIP_ETL" = true ] && echo 'No' || echo 'Sí')"
log_info "  Datos de muestra: $([ "$SAMPLE_DATA" = true ] && echo 'Sí' || echo 'No')"
log_info "  Ejecutar API: $([ "$RUN_API" = true ] && echo 'Sí' || echo 'No')"

echo ""

# 1. Verificar Python y dependencias
log_info "Verificando entorno Python..."

if ! command -v python3 &> /dev/null; then
    log_error "Python3 no encontrado. Instalar Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
log_success "Python $PYTHON_VERSION detectado"

# 2. Instalar/verificar dependencias
if [ -f "requirements.txt" ]; then
    log_info "Instalando dependencias..."
    python3 -m pip install -r requirements.txt --quiet
    log_success "Dependencias instaladas"
else
    log_warning "requirements.txt no encontrado"
fi

# 3. Verificar archivos necesarios
REQUIRED_FILES=(
    "setup_multi_city.py"
    "config_multicity.py"
    "database_optimized.py"
    "etl/multi_city_etl_complete.py"
    "api/routes/multi_city_optimized.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "Archivo requerido no encontrado: $file"
        exit 1
    fi
done

log_success "Todos los archivos requeridos encontrados"

# 4. Configurar sistema multi-ciudad
log_info "Configurando sistema multi-ciudad..."

SETUP_ARGS="--environment $ENVIRONMENT"

if [ "$SKIP_ETL" = true ]; then
    SETUP_ARGS="$SETUP_ARGS --skip-etl"
fi

if [ "$SAMPLE_DATA" = true ]; then
    SETUP_ARGS="$SETUP_ARGS --sample-data"
fi

if [ -n "$CITIES" ]; then
    SETUP_ARGS="$SETUP_ARGS --cities $CITIES"
fi

log_info "Ejecutando: python3 setup_multi_city.py $SETUP_ARGS"

if python3 setup_multi_city.py $SETUP_ARGS; then
    log_success "Configuración completada exitosamente"
else
    log_error "Error en configuración"
    exit 1
fi

# 5. Verificar estado del sistema
log_info "Verificando estado del sistema..."

# Verificar que existan datos
DATA_DIR="data/multi_city_optimized"
if [ -d "$DATA_DIR" ]; then
    DATA_COUNT=$(find "$DATA_DIR" -name "*_latest.csv" | wc -l)
    log_success "Encontrados datos para $DATA_COUNT ciudades"
else
    log_warning "Directorio de datos no encontrado"
fi

# 6. Ejecutar API si se solicita
if [ "$RUN_API" = true ]; then
    echo ""
    log_info "🌐 Iniciando API CleanSky Multi-Ciudad..."
    log_info "Puerto: $PORT"
    log_info "Documentación: http://localhost:$PORT/docs"
    log_info "Health Check: http://localhost:$PORT/health"
    log_info "Ciudades: http://localhost:$PORT/api/v2/cities"
    echo ""
    log_info "Presiona Ctrl+C para detener"
    echo ""
    
    # Configurar variables de entorno
    export PORT=$PORT
    export ENVIRONMENT=$ENVIRONMENT
    
    # Ejecutar API
    if command -v uvicorn &> /dev/null; then
        uvicorn main:app --host 0.0.0.0 --port $PORT --reload
    else
        # Fallback a Python directo
        python3 -c "
import uvicorn
uvicorn.run('main:app', host='0.0.0.0', port=$PORT, reload=True)
"
    fi
else
    echo ""
    log_success "🎉 Configuración completada!"
    log_info "Para ejecutar la API manualmente:"
    log_info "  export PORT=$PORT"
    log_info "  uvicorn main:app --host 0.0.0.0 --port $PORT --reload"
    echo ""
fi