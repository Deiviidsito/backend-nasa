"""
API Multi-Ciudad Optimizada - CleanSky North America  
Endpoints optimizados para manejar 3,000+ puntos por ciudad
"""
from fastapi import APIRouter, Query, HTTPException, Path, BackgroundTasks
from fastapi.responses import StreamingResponse
from pathlib import Path as PathLib
import pandas as pd
import numpy as np
import json
from typing import Dict, Any, List, Optional, Union
import asyncio
from datetime import datetime, timedelta
import logging
import io
import sys
import os
from functools import lru_cache
import redis
from contextlib import asynccontextmanager

# Agregar path para importaciones
sys.path.append(str(PathLib(__file__).parent.parent.parent))

from config_multicity import SUPPORTED_CITIES, MultiCitySettings

# Configurar logging
logger = logging.getLogger(__name__)

# Router
router = APIRouter(tags=["Multi-City Optimized"], prefix="/api/v2")

# Configuración
settings = MultiCitySettings()

# Cache Redis (opcional, fallback a memoria si no está disponible)
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("✅ Redis conectado para cache")
except:
    redis_client = None
    REDIS_AVAILABLE = False
    logger.warning("⚠️  Redis no disponible, usando cache en memoria")

# Cache en memoria como fallback
_memory_cache = {}
_city_data_cache = {}

class CityDataManager:
    """Gestor optimizado de datos por ciudad"""
    
    def __init__(self):
        self.cache_ttl = 3600  # 1 hora
        self.data_dir = PathLib("data/multi_city_processed")
    
    @lru_cache(maxsize=32)
    def get_city_config(self, city_id: str) -> Dict:
        """Obtiene configuración de ciudad (cached)"""
        if city_id not in SUPPORTED_CITIES:
            raise HTTPException(
                status_code=400,
                detail=f"Ciudad no soportada: {city_id}. Disponibles: {list(SUPPORTED_CITIES.keys())}"
            )
        return SUPPORTED_CITIES[city_id]
    
    async def load_city_data(self, city_id: str, use_cache: bool = True) -> pd.DataFrame:
        """
        Carga datos de ciudad optimizada con múltiples estrategias de cache
        """
        cache_key = f"city_data:{city_id}"
        
        # 1. Intentar cache Redis primero
        if REDIS_AVAILABLE and use_cache:
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    logger.debug(f"📦 Cache hit (Redis): {city_id}")
                    return pd.read_json(cached_data)
            except Exception as e:
                logger.warning(f"Error accediendo Redis: {e}")
        
        # 2. Cache en memoria
        if use_cache and cache_key in _city_data_cache:
            cache_entry = _city_data_cache[cache_key]
            if datetime.utcnow() - cache_entry['timestamp'] < timedelta(seconds=self.cache_ttl):
                logger.debug(f"📦 Cache hit (memoria): {city_id}")
                return cache_entry['data']
        
        # 3. Cargar desde disco
        try:
            city_data_file = self.data_dir / city_id / f"{city_id}_latest.csv"
            
            if not city_data_file.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Datos no encontrados para {city_id}. Ejecutar ETL primero."
                )
            
            # Carga optimizada con chunks para archivos grandes
            data = pd.read_csv(city_data_file)
            logger.info(f"💾 Datos cargados desde disco: {city_id} ({len(data)} puntos)")
            
            # Guardar en caches
            if use_cache:
                # Cache en memoria
                _city_data_cache[cache_key] = {
                    'data': data.copy(),
                    'timestamp': datetime.utcnow()
                }
                
                # Cache Redis (si está disponible)
                if REDIS_AVAILABLE:
                    try:
                        redis_client.setex(
                            cache_key, 
                            self.cache_ttl,
                            data.to_json(orient='records')
                        )
                        logger.debug(f"💾 Guardado en cache Redis: {city_id}")
                    except Exception as e:
                        logger.warning(f"Error guardando en Redis: {e}")
            
            return data
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error cargando datos para {city_id}: {str(e)}"
            )
    
    async def get_city_summary(self, city_id: str) -> Dict:
        """Obtiene resumen de ciudad desde JSON"""
        try:
            summary_file = self.data_dir / city_id / f"{city_id}_summary.json"
            
            if not summary_file.exists():
                # Generar resumen básico si no existe
                config = self.get_city_config(city_id)
                return {
                    "city_id": city_id,
                    "name": config["name"],
                    "bbox": config["bbox"],
                    "population": config["population"],
                    "timezone": config["timezone"],
                    "has_data": False,
                    "last_update": None
                }
            
            with open(summary_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error cargando resumen para {city_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error cargando resumen: {str(e)}")

# Instancia global del gestor
city_manager = CityDataManager()

@router.get("/cities", summary="Lista ciudades (optimizada)")
async def list_cities_optimized():
    """
    Lista todas las ciudades con información de estado optimizada.
    Incluye check rápido de disponibilidad de datos.
    """
    cities = []
    
    # Procesamiento en paralelo para checks de archivos
    async def check_city_data(city_id: str, config: Dict) -> Dict:
        try:
            summary = await city_manager.get_city_summary(city_id)
            return {
                "id": city_id,
                "name": config["name"],
                "bbox": {
                    "west": config["bbox"][0],
                    "south": config["bbox"][1], 
                    "east": config["bbox"][2],
                    "north": config["bbox"][3]
                },
                "population": config["population"],
                "timezone": config["timezone"],
                "has_data": summary.get("total_points", 0) > 0,
                "last_update": summary.get("last_update"),
                "total_points": summary.get("total_points", 0),
                "data_quality": summary.get("data_quality", {}),
                "air_quality_summary": summary.get("air_quality_summary", {}),
                "grid_resolution": config["grid_resolution"]
            }
        except:
            return {
                "id": city_id,
                "name": config["name"], 
                "has_data": False,
                "total_points": 0
            }
    
    # Ejecutar checks en paralelo
    tasks = [
        check_city_data(city_id, config) 
        for city_id, config in SUPPORTED_CITIES.items()
    ]
    
    cities = await asyncio.gather(*tasks)
    
    # Ordenar por población
    cities.sort(key=lambda x: x.get("population", 0), reverse=True)
    
    return {
        "total_cities": len(cities),
        "cities": cities,
        "coverage": "North America (TEMPO coverage area)",
        "cache_status": {
            "redis_available": REDIS_AVAILABLE,
            "memory_cache_size": len(_city_data_cache)
        }
    }

@router.get("/cities/{city_id}/data", summary="Datos completos de ciudad")
async def get_city_data_complete(
    city_id: str = Path(..., description="ID de la ciudad"),
    format: str = Query(default="json", regex="^(json|geojson|csv)$"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Límite de puntos (máx 10,000)"),
    bbox: Optional[str] = Query(None, description="Bounding box: west,south,east,north"),
    min_quality: Optional[float] = Query(None, ge=0.0, le=1.0, description="Calidad mínima de datos"),
    pollutants: Optional[str] = Query(None, description="Contaminantes específicos: no2,pm25,o3"),
    include_forecast: bool = Query(False, description="Incluir datos de pronóstico"),
    stream: bool = Query(False, description="Streaming para datasets grandes")
):
    """
    Obtiene datos completos de una ciudad con filtros avanzados y paginación.
    Optimizado para manejar 3,000+ puntos eficientemente.
    """
    # Validar ciudad
    config = city_manager.get_city_config(city_id)
    
    # Cargar datos
    data = await city_manager.load_city_data(city_id)
    
    # Aplicar filtros
    filtered_data = await apply_filters(data, bbox, min_quality, pollutants, limit)
    
    # Formatear respuesta según el tipo solicitado
    if format == "csv":
        return StreamingResponse(
            io.StringIO(filtered_data.to_csv(index=False)),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={city_id}_data.csv"}
        )
    
    elif format == "geojson":
        geojson = await convert_to_geojson(filtered_data, city_id)
        
        if stream and len(filtered_data) > 1000:
            return StreamingResponse(
                io.StringIO(json.dumps(geojson)),
                media_type="application/json"
            )
        return geojson
    
    else:  # JSON
        result = {
            "city_id": city_id,
            "name": config["name"],
            "bbox": config["bbox"],
            "total_points": len(data),
            "filtered_points": len(filtered_data),
            "last_update": filtered_data['timestamp'].max().isoformat() if 'timestamp' in filtered_data.columns else None,
            "data": filtered_data.to_dict('records')[:limit] if limit else filtered_data.to_dict('records')
        }
        
        if include_forecast:
            result["forecast"] = await get_forecast_data(city_id)
        
        return result

@router.get("/cities/{city_id}/latest", summary="Últimos datos (optimizado)")
async def get_city_latest_optimized(
    city_id: str = Path(..., description="ID de la ciudad"),
    format: str = Query(default="json", regex="^(json|geojson)$"),
    grid_resolution: Optional[float] = Query(None, description="Resolución de grilla personalizada"),
    aggregation: str = Query(default="mean", regex="^(mean|max|min|median)$")
):
    """
    Obtiene los últimos datos de una ciudad con opciones de agregación.
    Versión optimizada del endpoint original.
    """
    config = city_manager.get_city_config(city_id)
    data = await city_manager.load_city_data(city_id)
    
    # Aplicar agregación si se especifica una resolución diferente
    if grid_resolution and grid_resolution != config["grid_resolution"]:
        data = await aggregate_grid(data, grid_resolution, aggregation)
    
    if format == "geojson":
        return await convert_to_geojson(data, city_id)
    
    return {
        "city_id": city_id,
        "name": config["name"],
        "bbox": config["bbox"],
        "timestamp": data['timestamp'].max().isoformat() if 'timestamp' in data.columns else None,
        "grid_resolution": grid_resolution or config["grid_resolution"],
        "total_points": len(data),
        "air_quality_summary": {
            "mean_aqi": float(data['aqi_combined'].mean()) if 'aqi_combined' in data.columns else None,
            "max_aqi": float(data['aqi_combined'].max()) if 'aqi_combined' in data.columns else None,
            "dominant_category": data['air_quality_category'].mode().iloc[0] if 'air_quality_category' in data.columns and len(data) > 0 else None
        },
        "data": data.to_dict('records')
    }

@router.get("/cities/compare", summary="Comparar múltiples ciudades")
async def compare_cities(
    cities: str = Query(..., description="IDs de ciudades separadas por coma"),
    metric: str = Query(default="aqi_combined", description="Métrica a comparar"),
    aggregation: str = Query(default="mean", regex="^(mean|max|min|median)$")
):
    """
    Compara métricas entre múltiples ciudades.
    """
    city_ids = [city.strip() for city in cities.split(",")]
    
    if len(city_ids) > 10:
        raise HTTPException(status_code=400, detail="Máximo 10 ciudades para comparación")
    
    comparison_data = []
    
    # Cargar datos de todas las ciudades en paralelo
    tasks = []
    for city_id in city_ids:
        tasks.append(load_city_for_comparison(city_id, metric, aggregation))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for city_id, result in zip(city_ids, results):
        if isinstance(result, Exception):
            comparison_data.append({
                "city_id": city_id,
                "error": str(result),
                "value": None
            })
        else:
            comparison_data.append(result)
    
    return {
        "comparison": {
            "metric": metric,
            "aggregation": aggregation,
            "cities": comparison_data
        },
        "ranking": sorted(
            [city for city in comparison_data if city.get("value") is not None],
            key=lambda x: x["value"],
            reverse=True
        )
    }

@router.post("/cities/{city_id}/refresh", summary="Actualizar cache de ciudad")
async def refresh_city_cache(
    background_tasks: BackgroundTasks,
    city_id: str = Path(..., description="ID de la ciudad")
):
    """
    Fuerza la actualización del cache de una ciudad.
    """
    config = city_manager.get_city_config(city_id)
    
    # Limpiar cache
    cache_key = f"city_data:{city_id}"
    
    if REDIS_AVAILABLE:
        redis_client.delete(cache_key)
    
    if cache_key in _city_data_cache:
        del _city_data_cache[cache_key]
    
    # Recargar en background
    background_tasks.add_task(preload_city_data, city_id)
    
    return {
        "city_id": city_id,
        "name": config["name"],
        "cache_refreshed": True,
        "message": "Cache limpiado, recarga en progreso"
    }

@router.get("/cities/{city_id}/stats", summary="Estadísticas detalladas")
async def get_city_stats(
    city_id: str = Path(..., description="ID de la ciudad")
):
    """
    Obtiene estadísticas detalladas de una ciudad.
    """
    config = city_manager.get_city_config(city_id)
    data = await city_manager.load_city_data(city_id)
    
    # Calcular estadísticas
    stats = {
        "city_info": {
            "id": city_id,
            "name": config["name"],
            "population": config["population"],
            "timezone": config["timezone"]
        },
        "data_coverage": {
            "total_points": len(data),
            "points_with_no2": int((~data['no2_column'].isna()).sum()) if 'no2_column' in data.columns else 0,
            "points_with_pm25": int((~data['pm25_surface'].isna()).sum()) if 'pm25_surface' in data.columns else 0,
            "points_with_weather": int((~data['temperature'].isna()).sum()) if 'temperature' in data.columns else 0,
            "coverage_percentage": {
                "no2": float((~data['no2_column'].isna()).mean() * 100) if 'no2_column' in data.columns else 0,
                "pm25": float((~data['pm25_surface'].isna()).mean() * 100) if 'pm25_surface' in data.columns else 0,
                "weather": float((~data['temperature'].isna()).mean() * 100) if 'temperature' in data.columns else 0
            }
        },
        "air_quality_stats": {},
        "temporal_info": {
            "last_update": data['timestamp'].max().isoformat() if 'timestamp' in data.columns else None,
            "data_freshness_hours": None
        }
    }
    
    # Estadísticas de calidad del aire
    if 'aqi_combined' in data.columns:
        aqi_data = data['aqi_combined'].dropna()
        stats["air_quality_stats"] = {
            "mean_aqi": float(aqi_data.mean()),
            "median_aqi": float(aqi_data.median()),
            "max_aqi": float(aqi_data.max()),
            "min_aqi": float(aqi_data.min()),
            "std_aqi": float(aqi_data.std()),
            "percentiles": {
                "p25": float(aqi_data.quantile(0.25)),
                "p75": float(aqi_data.quantile(0.75)),
                "p90": float(aqi_data.quantile(0.90)),
                "p95": float(aqi_data.quantile(0.95))
            }
        }
        
        # Distribución por categorías
        if 'air_quality_category' in data.columns:
            category_counts = data['air_quality_category'].value_counts()
            stats["air_quality_stats"]["category_distribution"] = category_counts.to_dict()
    
    return stats

# Funciones auxiliares
async def apply_filters(data: pd.DataFrame, bbox: Optional[str], min_quality: Optional[float], 
                       pollutants: Optional[str], limit: Optional[int]) -> pd.DataFrame:
    """Aplica filtros a los datos"""
    filtered_data = data.copy()
    
    # Filtro por bounding box
    if bbox:
        try:
            west, south, east, north = map(float, bbox.split(','))
            filtered_data = filtered_data[
                (filtered_data['longitude'] >= west) &
                (filtered_data['longitude'] <= east) &
                (filtered_data['latitude'] >= south) &
                (filtered_data['latitude'] <= north)
            ]
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de bbox inválido")
    
    # Filtro por calidad
    if min_quality and 'data_quality' in filtered_data.columns:
        filtered_data = filtered_data[filtered_data['data_quality'] >= min_quality]
    
    # Filtro por contaminantes
    if pollutants:
        pollutant_list = [p.strip() for p in pollutants.split(',')]
        # Filtrar solo filas que tengan datos para los contaminantes solicitados
        for pollutant in pollutant_list:
            if pollutant == 'no2' and 'no2_column' in filtered_data.columns:
                filtered_data = filtered_data[~filtered_data['no2_column'].isna()]
            elif pollutant == 'pm25' and 'pm25_surface' in filtered_data.columns:
                filtered_data = filtered_data[~filtered_data['pm25_surface'].isna()]
            elif pollutant == 'o3' and 'o3_column' in filtered_data.columns:
                filtered_data = filtered_data[~filtered_data['o3_column'].isna()]
    
    # Aplicar límite
    if limit:
        filtered_data = filtered_data.head(limit)
    
    return filtered_data

async def convert_to_geojson(data: pd.DataFrame, city_id: str) -> Dict:
    """Convierte DataFrame a formato GeoJSON"""
    features = []
    
    for _, row in data.iterrows():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row['longitude'], row['latitude']]
            },
            "properties": {
                key: (value if pd.notna(value) else None)
                for key, value in row.items()
                if key not in ['longitude', 'latitude']
            }
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "city_id": city_id,
            "total_features": len(features),
            "generated_at": datetime.utcnow().isoformat()
        }
    }

async def aggregate_grid(data: pd.DataFrame, new_resolution: float, aggregation: str) -> pd.DataFrame:
    """Reagrega datos a una nueva resolución de grilla"""
    # Crear nueva grilla
    min_lon, max_lon = data['longitude'].min(), data['longitude'].max()
    min_lat, max_lat = data['latitude'].min(), data['latitude'].max()
    
    # Crear bins para agregación
    lon_bins = np.arange(min_lon, max_lon + new_resolution, new_resolution)
    lat_bins = np.arange(min_lat, max_lat + new_resolution, new_resolution)
    
    # Asignar puntos a bins
    data['lon_bin'] = pd.cut(data['longitude'], bins=lon_bins, include_lowest=True)
    data['lat_bin'] = pd.cut(data['latitude'], bins=lat_bins, include_lowest=True)
    
    # Función de agregación
    agg_func = getattr(np, aggregation)
    
    # Agrupar y agregar
    numeric_columns = data.select_dtypes(include=[np.number]).columns
    
    aggregated = data.groupby(['lon_bin', 'lat_bin'])[numeric_columns].agg(agg_func).reset_index()
    
    # Calcular coordenadas centrales de bins
    aggregated['longitude'] = aggregated['lon_bin'].apply(lambda x: x.mid)
    aggregated['latitude'] = aggregated['lat_bin'].apply(lambda x: x.mid)
    
    # Limpiar columnas temporales
    aggregated = aggregated.drop(['lon_bin', 'lat_bin'], axis=1)
    
    return aggregated

async def get_forecast_data(city_id: str) -> Dict:
    """Obtiene datos de pronóstico para una ciudad (placeholder)"""
    # Implementar lógica de pronóstico
    return {
        "available": False,
        "message": "Pronóstico no implementado aún"
    }

async def load_city_for_comparison(city_id: str, metric: str, aggregation: str) -> Dict:
    """Carga datos de ciudad para comparación"""
    try:
        config = city_manager.get_city_config(city_id)
        data = await city_manager.load_city_data(city_id)
        
        if metric not in data.columns:
            raise ValueError(f"Métrica {metric} no disponible para {city_id}")
        
        # Calcular valor agregado
        agg_func = getattr(data[metric], aggregation)
        value = float(agg_func())
        
        return {
            "city_id": city_id,
            "name": config["name"],
            "population": config["population"],
            "value": value,
            "total_points": len(data)
        }
        
    except Exception as e:
        raise Exception(f"Error cargando {city_id}: {str(e)}")

async def preload_city_data(city_id: str):
    """Precarga datos de ciudad en background"""
    try:
        await city_manager.load_city_data(city_id, use_cache=False)
        logger.info(f"✅ Datos precargados para {city_id}")
    except Exception as e:
        logger.error(f"❌ Error precargando {city_id}: {e}")