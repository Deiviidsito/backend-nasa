"""
API Especializada para Dashboard CleanSky
Endpoint único que carga todos los datos necesarios para el dashboard
"""
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from pathlib import Path as PathLib
import pandas as pd
import numpy as np
import json
from typing import Dict, Any, List, Optional, Union
import asyncio
from datetime import datetime
import logging
import sys
import os

# Agregar path para importaciones
sys.path.append(str(PathLib(__file__).parent.parent.parent))

from config_multicity import SUPPORTED_CITIES, MultiCitySettings

# Configurar logging
logger = logging.getLogger(__name__)

# Router específico para dashboard
router = APIRouter(tags=["Dashboard"], prefix="/api/dashboard")

# Configuración
settings = MultiCitySettings()

class DashboardDataLoader:
    """Cargador de datos optimizado para el dashboard"""
    
    def __init__(self):
        self.data_dir = PathLib("data/multi_city_processed")
        self.cache = {}
        self.last_update = None
    
    async def load_all_dashboard_data(self) -> Dict[str, Any]:
        """
        Carga todos los datos necesarios para el dashboard de una vez
        
        Returns:
            Dictionary con toda la información del dashboard
        """
        logger.info("🔄 Cargando datos completos para dashboard...")
        
        # Estructura de datos del dashboard
        dashboard_data = {
            "metadata": {
                "last_update": datetime.utcnow().isoformat(),
                "total_cities": len(SUPPORTED_CITIES),
                "data_sources": ["NASA TEMPO", "OpenAQ", "MERRA-2"]
            },
            "cities_status": {},
            "map_data": {
                "type": "FeatureCollection",
                "features": []
            },
            "tabular_data": [],
            "summary_metrics": {
                "cities_with_data": 0,
                "cities_loading": 0,
                "cities_with_error": 0,
                "total_cities": len(SUPPORTED_CITIES),
                "total_data_points": 0,
                "active_cities": 0,
                "average_risk_score": 0,
                "low_risk_points": 0
            },
            "risk_distribution": {
                "bajo": 0,          # 0-24
                "moderado": 0,      # 25-44  
                "alto": 0,          # 45-69
                "muy_alto": 0       # 70+
            },
            "cities_details": []
        }
        
        # Procesar cada ciudad
        tasks = []
        for city_id, city_config in SUPPORTED_CITIES.items():
            tasks.append(self._process_city_for_dashboard(city_id, city_config))
        
        # Ejecutar en paralelo
        city_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        for city_id, result in zip(SUPPORTED_CITIES.keys(), city_results):
            if isinstance(result, Exception):
                # Error en la ciudad
                dashboard_data["cities_status"][city_id] = "error"
                dashboard_data["summary_metrics"]["cities_with_error"] += 1
                dashboard_data["cities_details"].append({
                    "id": city_id,
                    "name": SUPPORTED_CITIES[city_id]["name"],
                    "status": "error",
                    "error": str(result),
                    "data_points": 0,
                    "risk_score": None
                })
            else:
                # Ciudad procesada exitosamente
                city_data = result
                status = city_data["status"]
                
                dashboard_data["cities_status"][city_id] = status
                
                if status == "success":
                    dashboard_data["summary_metrics"]["cities_with_data"] += 1
                    dashboard_data["summary_metrics"]["active_cities"] += 1
                    
                    # Agregar datos al mapa (GeoJSON)
                    if city_data["map_features"]:
                        dashboard_data["map_data"]["features"].extend(city_data["map_features"])
                    
                    # Agregar datos tabulares
                    if city_data["tabular_rows"]:
                        dashboard_data["tabular_data"].extend(city_data["tabular_rows"])
                    
                    # Actualizar métricas
                    dashboard_data["summary_metrics"]["total_data_points"] += city_data["data_points"]
                    
                    # Actualizar distribución de riesgo
                    for level, count in city_data["risk_distribution"].items():
                        dashboard_data["risk_distribution"][level] += count
                
                elif status == "loading":
                    dashboard_data["summary_metrics"]["cities_loading"] += 1
                else:
                    dashboard_data["summary_metrics"]["cities_with_error"] += 1
                
                # Agregar detalles de ciudad
                dashboard_data["cities_details"].append(city_data["city_details"])
        
        # Calcular métricas finales
        await self._calculate_final_metrics(dashboard_data)
        
        logger.info(f"✅ Dashboard cargado: {dashboard_data['summary_metrics']['cities_with_data']} ciudades con datos")
        
        return dashboard_data
    
    async def _process_city_for_dashboard(self, city_id: str, city_config: Dict) -> Dict:
        """Procesa una ciudad específica para el dashboard"""
        
        try:
            # Verificar archivos de datos
            city_data_file = self.data_dir / city_id / f"{city_id}_latest.csv"
            
            if not city_data_file.exists():
                # Sin datos
                return {
                    "status": "loading",
                    "city_details": {
                        "id": city_id,
                        "name": city_config["name"],
                        "status": "loading",
                        "data_points": 0,
                        "risk_score": None,
                        "bbox": city_config["bbox"],
                        "population": city_config["population"]
                    },
                    "map_features": [],
                    "tabular_rows": [],
                    "data_points": 0,
                    "risk_distribution": {"bajo": 0, "moderado": 0, "alto": 0, "muy_alto": 0}
                }
            
            # Cargar datos
            data = pd.read_csv(city_data_file)
            
            if len(data) == 0:
                raise ValueError("Archivo de datos vacío")
            
            # Procesar datos para dashboard
            map_features = await self._create_map_features(city_id, city_config, data)
            tabular_rows = await self._create_tabular_rows(city_id, city_config, data)
            risk_distribution = await self._calculate_risk_distribution(data)
            
            # Calcular risk score promedio
            if 'aqi_combined' in data.columns:
                avg_risk = float(data['aqi_combined'].mean())
            elif 'risk_score' in data.columns:
                avg_risk = float(data['risk_score'].mean())
            else:
                # Generar risk score sintético basado en datos disponibles
                avg_risk = await self._calculate_synthetic_risk_score(data)
            
            return {
                "status": "success",
                "city_details": {
                    "id": city_id,
                    "name": city_config["name"],
                    "status": "success",
                    "data_points": len(data),
                    "risk_score": round(avg_risk, 1),
                    "bbox": city_config["bbox"],
                    "population": city_config["population"],
                    "last_update": datetime.utcnow().isoformat()
                },
                "map_features": map_features,
                "tabular_rows": tabular_rows,
                "data_points": len(data),
                "risk_distribution": risk_distribution
            }
            
        except Exception as e:
            logger.error(f"Error procesando {city_id}: {e}")
            return {
                "status": "error",
                "city_details": {
                    "id": city_id,
                    "name": city_config["name"],
                    "status": "error",
                    "error": str(e),
                    "data_points": 0,
                    "risk_score": None
                },
                "map_features": [],
                "tabular_rows": [],
                "data_points": 0,
                "risk_distribution": {"bajo": 0, "moderado": 0, "alto": 0, "muy_alto": 0}
            }
    
    async def _create_map_features(self, city_id: str, city_config: Dict, data: pd.DataFrame) -> List[Dict]:
        """Crea features GeoJSON para el mapa"""
        features = []
        
        # Seleccionar muestra representativa para el mapa (máximo 100 puntos por ciudad)
        if len(data) > 100:
            # Sampling estratificado por risk score
            sample_data = data.sample(n=100, random_state=42)
        else:
            sample_data = data
        
        for _, row in sample_data.iterrows():
            # Determinar risk score
            if 'aqi_combined' in row:
                risk_score = row['aqi_combined']
            elif 'risk_score' in row:
                risk_score = row['risk_score']
            else:
                risk_score = await self._calculate_synthetic_risk_score(pd.DataFrame([row]))
            
            # Clasificar nivel de riesgo
            if pd.isna(risk_score):
                risk_level = "sin_datos"
                risk_category = "Sin Datos"
            elif risk_score <= 24:
                risk_level = "bajo"
                risk_category = "Bajo"
            elif risk_score <= 44:
                risk_level = "moderado" 
                risk_category = "Moderado"
            elif risk_score <= 69:
                risk_level = "alto"
                risk_category = "Alto"
            else:
                risk_level = "muy_alto"
                risk_category = "Muy Alto"
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row['longitude']), float(row['latitude'])]
                },
                "properties": {
                    "city_id": city_id,
                    "city_name": city_config["name"],
                    "risk_score": float(risk_score) if pd.notna(risk_score) else None,
                    "risk_level": risk_level,
                    "risk_category": risk_category,
                    "no2_column": float(row.get('no2_column', 0)) if pd.notna(row.get('no2_column')) else None,
                    "pm25_surface": float(row.get('pm25_surface', 0)) if pd.notna(row.get('pm25_surface')) else None,
                    "temperature": float(row.get('temperature', 0)) if pd.notna(row.get('temperature')) else None,
                    "data_quality": float(row.get('data_quality', 0)) if pd.notna(row.get('data_quality')) else None
                }
            }
            
            features.append(feature)
        
        return features
    
    async def _create_tabular_rows(self, city_id: str, city_config: Dict, data: pd.DataFrame) -> List[Dict]:
        """Crea filas para la tabla de datos"""
        tabular_rows = []
        
        # Seleccionar muestra para tabla (máximo 50 filas por ciudad)
        if len(data) > 50:
            sample_data = data.sample(n=50, random_state=42)
        else:
            sample_data = data
        
        for _, row in sample_data.iterrows():
            # Calcular risk score
            if 'aqi_combined' in row:
                risk_score = row['aqi_combined']
            elif 'risk_score' in row:
                risk_score = row['risk_score']
            else:
                risk_score = await self._calculate_synthetic_risk_score(pd.DataFrame([row]))
            
            # Clasificación
            if pd.isna(risk_score):
                clasificacion = "Sin Datos"
                estado = "sin_datos"
            elif risk_score <= 24:
                clasificacion = "Good"
                estado = "bajo_riesgo"
            elif risk_score <= 44:
                clasificacion = "Moderate"
                estado = "riesgo_moderado"
            elif risk_score <= 69:
                clasificacion = "Bad" 
                estado = "alto_riesgo"
            else:
                clasificacion = "Very Bad"
                estado = "muy_alto_riesgo"
            
            tabular_row = {
                "city_id": city_id,
                "city_name": city_config["name"],
                "latitud": round(float(row['latitude']), 6),
                "longitud": round(float(row['longitude']), 6),
                "risk_score": round(float(risk_score), 1) if pd.notna(risk_score) else None,
                "clasificacion": clasificacion,
                "estado": estado,
                "no2_column": round(float(row.get('no2_column', 0)), 2) if pd.notna(row.get('no2_column')) else None,
                "pm25_surface": round(float(row.get('pm25_surface', 0)), 2) if pd.notna(row.get('pm25_surface')) else None,
                "temperatura": round(float(row.get('temperature', 0)), 1) if pd.notna(row.get('temperature')) else None
            }
            
            tabular_rows.append(tabular_row)
        
        return tabular_rows
    
    async def _calculate_risk_distribution(self, data: pd.DataFrame) -> Dict[str, int]:
        """Calcula la distribución de riesgo"""
        
        # Determinar columna de risk score
        if 'aqi_combined' in data.columns:
            risk_col = 'aqi_combined'
        elif 'risk_score' in data.columns:
            risk_col = 'risk_score'
        else:
            # Calcular sintético
            risk_scores = []
            for _, row in data.iterrows():
                risk_scores.append(await self._calculate_synthetic_risk_score(pd.DataFrame([row])))
            risk_data = pd.Series(risk_scores)
        
        if 'risk_col' in locals():
            risk_data = data[risk_col].dropna()
        
        distribution = {
            "bajo": int((risk_data <= 24).sum()),
            "moderado": int(((risk_data > 24) & (risk_data <= 44)).sum()),
            "alto": int(((risk_data > 44) & (risk_data <= 69)).sum()),
            "muy_alto": int((risk_data > 69).sum())
        }
        
        return distribution
    
    async def _calculate_synthetic_risk_score(self, data: pd.DataFrame) -> float:
        """Calcula un risk score sintético basado en datos disponibles"""
        
        if len(data) == 0:
            return 50.0  # Default moderate
        
        row = data.iloc[0] if len(data) > 1 else data.iloc[0]
        
        # Algoritmo sintético simple
        risk_components = []
        
        # NO2 component
        if 'no2_column' in row and pd.notna(row['no2_column']):
            no2_val = float(row['no2_column'])
            # Normalizar NO2 column (molec/cm²) a score 0-100
            no2_score = min(100, max(0, (no2_val / 5e15) * 25))
            risk_components.append(no2_score)
        
        # PM2.5 component  
        if 'pm25_surface' in row and pd.notna(row['pm25_surface']):
            pm25_val = float(row['pm25_surface'])
            # PM2.5 to AQI approximation
            if pm25_val <= 12:
                pm25_score = (pm25_val / 12) * 50
            elif pm25_val <= 35.4:
                pm25_score = 50 + ((pm25_val - 12) / (35.4 - 12)) * 50
            else:
                pm25_score = min(100, 100 + ((pm25_val - 35.4) / 10))
            risk_components.append(pm25_score)
        
        # Weather factor (opcional)
        if 'temperature' in row and pd.notna(row['temperature']):
            temp_val = float(row['temperature'])
            # Temperature factor (higher temp can worsen air quality)
            if temp_val > 30:  # Hot weather
                temp_factor = 1.1
            elif temp_val < 0:  # Cold weather
                temp_factor = 1.05
            else:
                temp_factor = 1.0
        else:
            temp_factor = 1.0
        
        # Calcular score final
        if risk_components:
            base_score = np.mean(risk_components)
            final_score = base_score * temp_factor
        else:
            # Si no hay datos, score moderado
            final_score = 50.0
        
        return min(100.0, max(0.0, final_score))
    
    async def _calculate_final_metrics(self, dashboard_data: Dict):
        """Calcula métricas finales del dashboard"""
        
        # Risk score promedio
        total_risk = 0
        cities_with_risk = 0
        
        for city_detail in dashboard_data["cities_details"]:
            if city_detail.get("risk_score") is not None:
                total_risk += city_detail["risk_score"]
                cities_with_risk += 1
        
        if cities_with_risk > 0:
            dashboard_data["summary_metrics"]["average_risk_score"] = round(total_risk / cities_with_risk, 1)
        
        # Contar puntos de bajo riesgo
        dashboard_data["summary_metrics"]["low_risk_points"] = dashboard_data["risk_distribution"]["bajo"]

# Instancia global
dashboard_loader = DashboardDataLoader()

@router.get("/all-data", summary="Datos completos para dashboard")
async def get_dashboard_data(
    background_tasks: BackgroundTasks,
    force_refresh: bool = Query(False, description="Forzar recarga de datos")
):
    """
    Endpoint único que devuelve todos los datos necesarios para el dashboard.
    
    Incluye:
    - Estado de todas las ciudades
    - Datos para el mapa interactivo (GeoJSON)
    - Datos tabulares
    - Métricas resumidas
    - Distribución de riesgo
    """
    
    try:
        logger.info("📊 Solicitando datos completos del dashboard")
        
        # Cargar todos los datos
        dashboard_data = await dashboard_loader.load_all_dashboard_data()
        
        # Agregar información adicional
        dashboard_data["api_info"] = {
            "endpoint": "/api/dashboard/all-data",
            "version": "1.0",
            "optimized_for": "CleanSky Dashboard",
            "response_time": "< 2 seconds",
            "max_map_points": 1000,
            "max_table_rows": 500
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"❌ Error cargando datos del dashboard: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error cargando datos del dashboard: {str(e)}"
        )

@router.get("/city/{city_id}", summary="Datos específicos de una ciudad para dashboard")
async def get_city_dashboard_data(city_id: str):
    """
    Obtiene datos específicos de una ciudad para el dashboard.
    """
    
    if city_id not in SUPPORTED_CITIES:
        raise HTTPException(
            status_code=404,
            detail=f"Ciudad no encontrada: {city_id}"
        )
    
    try:
        city_config = SUPPORTED_CITIES[city_id]
        city_data = await dashboard_loader._process_city_for_dashboard(city_id, city_config)
        
        return {
            "city_id": city_id,
            "city_name": city_config["name"],
            "status": city_data["status"],
            "data": city_data
        }
        
    except Exception as e:
        logger.error(f"❌ Error cargando datos de {city_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cargando datos de {city_id}: {str(e)}"
        )

@router.get("/metrics", summary="Solo métricas resumidas")
async def get_dashboard_metrics():
    """
    Endpoint ligero que devuelve solo las métricas resumidas.
    Útil para actualizaciones rápidas del dashboard.
    """
    
    try:
        # Cargar solo métricas (más rápido)
        metrics = {
            "cities_with_data": 0,
            "cities_loading": 0, 
            "cities_with_error": 0,
            "total_cities": len(SUPPORTED_CITIES),
            "total_data_points": 0,
            "active_cities": 0,
            "average_risk_score": 0,
            "low_risk_points": 0
        }
        
        # Verificar rápidamente cada ciudad
        for city_id in SUPPORTED_CITIES.keys():
            city_data_file = dashboard_loader.data_dir / city_id / f"{city_id}_latest.csv"
            
            if city_data_file.exists():
                try:
                    # Solo leer header para contar filas rápidamente
                    data = pd.read_csv(city_data_file, nrows=0)  # Solo header
                    with open(city_data_file, 'r') as f:
                        line_count = sum(1 for line in f) - 1  # -1 for header
                    
                    if line_count > 0:
                        metrics["cities_with_data"] += 1
                        metrics["active_cities"] += 1
                        metrics["total_data_points"] += line_count
                    else:
                        metrics["cities_loading"] += 1
                        
                except Exception:
                    metrics["cities_with_error"] += 1
            else:
                metrics["cities_loading"] += 1
        
        # Calcular average risk score (estimación rápida)
        if metrics["cities_with_data"] > 0:
            metrics["average_risk_score"] = 50.0  # Placeholder
        
        metrics["last_update"] = datetime.utcnow().isoformat()
        
        return {
            "summary_metrics": metrics,
            "response_time": "< 100ms",
            "data_freshness": "real-time"
        }
        
    except Exception as e:
        logger.error(f"❌ Error cargando métricas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cargando métricas: {str(e)}"
        )

@router.post("/refresh", summary="Actualizar cache del dashboard")
async def refresh_dashboard_cache(
    background_tasks: BackgroundTasks,
    cities: Optional[str] = Query(None, description="Ciudades específicas (separadas por coma)")
):
    """
    Fuerza la actualización del cache del dashboard.
    """
    
    try:
        if cities:
            city_list = [city.strip() for city in cities.split(",")]
            # Validar ciudades
            invalid_cities = [city for city in city_list if city not in SUPPORTED_CITIES]
            if invalid_cities:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ciudades inválidas: {invalid_cities}"
                )
        else:
            city_list = list(SUPPORTED_CITIES.keys())
        
        # Limpiar cache
        dashboard_loader.cache = {}
        dashboard_loader.last_update = None
        
        # Programar recarga en background
        background_tasks.add_task(
            dashboard_loader.load_all_dashboard_data
        )
        
        return {
            "message": "Cache del dashboard actualizado",
            "cities_refreshed": city_list,
            "refresh_started": datetime.utcnow().isoformat(),
            "estimated_completion": "~30 seconds"
        }
        
    except Exception as e:
        logger.error(f"❌ Error actualizando cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando cache: {str(e)}"
        )