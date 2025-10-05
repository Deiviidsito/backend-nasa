# 🌍 CleanSky Multi-Ciudad - Sistema Optimizado

Sistema completo para monitoreo de calidad del aire en múltiples ciudades de Norte América usando datos NASA TEMPO, optimizado para manejar **3,000+ puntos por ciudad**.

## 🚀 Características Principales

### ✨ **Capacidades del Sistema**
- 📍 **10 ciudades soportadas** dentro del dominio TEMPO de NASA
- 🎯 **3,000+ puntos por ciudad** con resolución de ~800m
- ⚡ **API optimizada** con cache Redis y consultas espaciales
- 🗄️ **Base de datos flexible** (PostgreSQL/SQLite/FileSystem)
- 🔄 **ETL completo** con fusión de múltiples fuentes de datos
- 📊 **Métricas de calidad del aire** con AQI en tiempo real

### 🏙️ **Ciudades Soportadas**
1. **Los Angeles, CA** - 3,971,883 habitantes
2. **New York, NY** - 8,336,817 habitantes  
3. **Chicago, IL** - 2,693,976 habitantes
4. **Houston, TX** - 2,320,268 habitantes
5. **Phoenix, AZ** - 1,608,139 habitantes
6. **Seattle, WA** - 753,675 habitantes
7. **Miami, FL** - 442,241 habitantes
8. **Denver, CO** - 715,522 habitantes
9. **Boston, MA** - 685,094 habitantes
10. **Atlanta, GA** - 486,290 habitantes

### 📡 **Fuentes de Datos**
- **NASA TEMPO**: NO₂ y O₃ troposférico
- **OpenAQ**: PM2.5 de estaciones terrestres
- **NASA MERRA-2**: Datos meteorológicos
- **Fusión inteligente**: Interpolación espacial y temporal

## 🛠️ Instalación y Configuración

### Prerrequisitos
```bash
# Python 3.8+
python3 --version

# Dependencias del sistema (opcional)
sudo apt-get install postgresql-client redis-server  # Ubuntu
brew install postgresql redis                        # macOS
```

### 1. Configuración Rápida
```bash
# Clonar y configurar
git clone <tu-repo>
cd backend

# Instalar dependencias
pip install -r requirements.txt

# Configuración completa con datos de muestra
./run_multi_city.sh --sample-data

# O configuración con datos reales (requiere credenciales NASA)
./run_multi_city.sh --environment production_sqlite
```

### 2. Configuración Avanzada
```bash
# Configuración personalizada
python3 setup_multi_city.py \
    --environment production_postgresql \
    --cities los_angeles new_york chicago \
    --sample-data

# Solo configurar base de datos sin ETL
python3 setup_multi_city.py \
    --skip-etl \
    --environment development
```

### 3. Variables de Entorno
```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost/cleansky
REDIS_URL=redis://localhost:6379/0
NASA_EARTHDATA_USERNAME=tu_usuario
NASA_EARTHDATA_PASSWORD=tu_password
OPENAQ_API_KEY=tu_api_key
```

## 🌐 API Endpoints

### 🔗 **Endpoints Base (v1)**
```
GET  /api/cities                    # Lista de ciudades
GET  /api/cities/{city_id}/latest   # Últimos datos
POST /api/cities/compare            # Comparar ciudades
```

### ⚡ **Endpoints Optimizados (v2)**
```
GET  /api/v2/cities                           # Lista con estadísticas
GET  /api/v2/cities/{city_id}/data           # Datos completos con filtros
GET  /api/v2/cities/{city_id}/latest         # Datos recientes optimizados
GET  /api/v2/cities/{city_id}/stats          # Estadísticas detalladas
GET  /api/v2/cities/compare                  # Comparación multi-ciudad
POST /api/v2/cities/{city_id}/refresh        # Actualizar cache
```

### 📊 **Parámetros de Consulta Avanzados**
```bash
# Filtros espaciales
GET /api/v2/cities/los_angeles/data?bbox=-118.5,33.8,-118.0,34.2

# Filtros de calidad
GET /api/v2/cities/new_york/data?min_quality=0.8&limit=1000

# Contaminantes específicos
GET /api/v2/cities/chicago/data?pollutants=no2,pm25

# Agregación temporal
GET /api/v2/cities/houston/latest?aggregation=median&grid_resolution=0.01

# Formatos de salida
GET /api/v2/cities/seattle/data?format=geojson
GET /api/v2/cities/miami/data?format=csv
```

## 💾 Configuración de Base de Datos

### Opciones de Almacenamiento

#### 1. **Sistema de Archivos** (Desarrollo)
```python
# Automático, sin configuración adicional
# Usa archivos Parquet comprimidos + índices JSON
```

#### 2. **SQLite** (Producción pequeña/media)
```bash
# Configuración automática
python3 setup_multi_city.py --environment production_sqlite
```

#### 3. **PostgreSQL** (Producción grande)
```sql
-- Crear base de datos
CREATE DATABASE cleansky;
CREATE EXTENSION postgis;  -- Para consultas espaciales

-- Usuario dedicado
CREATE USER cleansky_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE cleansky TO cleansky_user;
```

```bash
# Configurar
export DATABASE_URL="postgresql://cleansky_user:secure_password@localhost/cleansky"
python3 setup_multi_city.py --environment production_postgresql
```

### Optimizaciones de Rendimiento

#### PostgreSQL
```sql
-- Configuraciones recomendadas
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB'; 
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET random_page_cost = 1.1;
SELECT pg_reload_conf();
```

#### Redis Cache
```bash
# Instalar Redis
brew install redis          # macOS
sudo apt install redis      # Ubuntu

# Configurar
export REDIS_URL="redis://localhost:6379/0"
```

## 🔄 ETL y Procesamiento de Datos

### Ejecución Manual del ETL
```bash
# ETL completo para todas las ciudades
python3 -m etl.multi_city_etl_complete

# Ciudades específicas
python3 -m etl.multi_city_etl_complete --cities los_angeles new_york

# Modo test con datos sintéticos
python3 -m etl.multi_city_etl_complete --test
```

### Programación Automática
```bash
# Crontab para actualización horaria
0 * * * * cd /path/to/backend && python3 -m etl.multi_city_etl_complete

# O usando systemd timer
# /etc/systemd/system/cleansky-etl.timer
[Unit]
Description=CleanSky ETL Timer

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

## 📈 Monitoreo y Métricas

### Health Checks
```bash
# Estado general
curl http://localhost:8000/health

# Estadísticas de ciudad
curl http://localhost:8000/api/v2/cities/los_angeles/stats

# Performance de cache
curl http://localhost:8000/api/v2/cities | jq '.cache_status'
```

### Métricas de Rendimiento
- **Carga de datos**: < 1 segundo para 3,000 puntos
- **Consultas espaciales**: < 500ms para areas pequeñas
- **Cache hit rate**: > 80% en producción
- **API response time**: < 200ms para consultas cached

### Logs y Debugging
```bash
# Logs del ETL
tail -f logs/etl_multi_city.log

# Logs de la API
tail -f logs/api.log

# Logs de setup
tail -f setup_multi_city.log
```

## 🔧 Troubleshooting

### Problemas Comunes

#### 1. **Error de conexión a base de datos**
```bash
# Verificar conexión
python3 -c "from database_optimized import get_storage; import asyncio; asyncio.run(get_storage().initialize())"

# Recrear tablas
python3 setup_multi_city.py --environment production_sqlite --skip-etl
```

#### 2. **Sin datos para una ciudad**
```bash
# Verificar archivos
ls -la data/multi_city_optimized/los_angeles/

# Regenerar datos
python3 -m etl.multi_city_etl_complete --cities los_angeles --test
```

#### 3. **Performance lenta**
```bash
# Verificar índices
python3 -c "from database_optimized import *; import asyncio; asyncio.run(get_storage().initialize())"

# Limpiar cache
redis-cli FLUSHDB  # Si usas Redis
```

#### 4. **Errores de memoria**
```bash
# Reducir batch size en ETL
export ETL_BATCH_SIZE=500

# Usar streaming para consultas grandes
curl "http://localhost:8000/api/v2/cities/new_york/data?stream=true&limit=5000"
```

### Logs de Debugging
```python
# Habilitar debug logging
import logging
logging.getLogger().setLevel(logging.DEBUG)

# En config_multicity.py
DEBUG = True
```

## 🚀 Despliegue en Producción

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python3 setup_multi_city.py --environment production_sqlite --sample-data

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Render/Railway
```bash
# Build command
python3 setup_multi_city.py --environment production_sqlite --sample-data --skip-etl

# Start command  
python3 start_render.py
```

### AWS/GCP
```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/cleansky
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  db:
    image: postgis/postgis:13-3.1
    environment:
      POSTGRES_DB: cleansky
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## 📊 Ejemplos de Uso

### 1. **Obtener datos de Los Angeles**
```python
import requests

# Datos básicos
response = requests.get("http://localhost:8000/api/v2/cities/los_angeles/latest")
data = response.json()

print(f"Ciudad: {data['name']}")
print(f"Puntos: {data['total_points']}")
print(f"AQI promedio: {data['air_quality_summary']['mean_aqi']}")
```

### 2. **Consulta espacial en área específica**
```python
# Filtrar por bounding box (downtown LA)
bbox = "-118.3,34.0,-118.2,34.1"
response = requests.get(
    f"http://localhost:8000/api/v2/cities/los_angeles/data?bbox={bbox}&limit=500"
)

points = response.json()['data']
print(f"Puntos en downtown LA: {len(points)}")
```

### 3. **Comparar múltiples ciudades**
```python
# Comparar AQI entre ciudades
response = requests.get(
    "http://localhost:8000/api/v2/cities/compare?cities=los_angeles,new_york,chicago&metric=aqi_combined"
)

ranking = response.json()['ranking']
for city in ranking:
    print(f"{city['name']}: AQI {city['value']:.1f}")
```

### 4. **Datos en formato GeoJSON**
```python
# Para usar en mapas web
response = requests.get(
    "http://localhost:8000/api/v2/cities/seattle/data?format=geojson&limit=1000"
)

geojson = response.json()
# Usar con Leaflet, Mapbox, etc.
```

## 📚 Recursos Adicionales

### Documentación
- **API Docs**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Datasets
- **NASA TEMPO**: https://tempo.si.edu/
- **OpenAQ**: https://openaq.org/
- **NASA MERRA-2**: https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/

### Papers y Referencias
- TEMPO Mission Overview
- Air Quality Index Calculation Methods
- Spatial Data Interpolation Techniques

## 🤝 Contribuir

### Agregar Nueva Ciudad
1. Actualizar `SUPPORTED_CITIES` en `config_multicity.py`
2. Verificar cobertura TEMPO para la región
3. Ejecutar `python3 setup_multi_city.py --cities nueva_ciudad`
4. Probar endpoints nuevos

### Mejoras de Performance
1. Optimizar consultas en `database_optimized.py`
2. Agregar nuevos índices espaciales
3. Implementar cache más inteligente
4. Paralelizar procesamiento ETL

---

## 🎯 **¡Tu Sistema Está Listo!**

Con esta configuración tienes un sistema completo de monitoreo de calidad del aire multi-ciudad que puede manejar **más de 30,000 puntos totales** (3,000+ por ciudad) con excelente rendimiento.

**¡Comienza ahora:**
```bash
./run_multi_city.sh --sample-data
```

**API estará disponible en:** http://localhost:8000/docs