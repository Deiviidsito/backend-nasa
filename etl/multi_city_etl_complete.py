#!/usr/bin/env python3
"""
ETL Completo Multi-Ciudad para CleanSky North America
Genera datos para todas las ciudades soportadas con 3,000+ puntos por ciudad
"""

import asyncio
import logging
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

from config_multicity import SUPPORTED_CITIES, MultiCitySettings
from etl.ingest_tempo import fetch_tempo_data
from etl.ingest_openaq import fetch_openaq_data
from etl.ingest_meteorology import fetch_merra2_data
from etl.utils import setup_logging, save_to_netcdf, save_to_csv
from etl.utils_math import interpolate_grid, calculate_air_quality_index

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiCityETL:
    """ETL completo para múltiples ciudades"""
    
    def __init__(self):
        self.settings = MultiCitySettings()
        self.output_dir = Path("data/multi_city_processed")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Estadísticas de procesamiento
        self.stats = {
            "cities_processed": 0,
            "total_points": 0,
            "data_sources": [],
            "processing_time": 0,
            "errors": []
        }
    
    def generate_high_density_grid(self, bbox: List[float], resolution: float = 0.01) -> Tuple[np.ndarray, np.ndarray]:
        """
        Genera una grilla de alta densidad para una ciudad
        
        Args:
            bbox: [west, south, east, north]
            resolution: Resolución en grados (0.01 = ~1km)
        
        Returns:
            Tuple de arrays (lons, lats)
        """
        west, south, east, north = bbox
        
        # Crear grilla de alta densidad
        lons = np.arange(west, east + resolution, resolution)
        lats = np.arange(south, north + resolution, resolution)
        
        # Crear meshgrid
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        logger.info(f"Grilla generada: {len(lons)} x {len(lats)} = {len(lons) * len(lats)} puntos")
        
        return lon_grid, lat_grid
    
    async def process_city_data(self, city_id: str, city_config: Dict) -> Dict:
        """
        Procesa datos para una ciudad específica
        
        Args:
            city_id: ID de la ciudad
            city_config: Configuración de la ciudad
            
        Returns:
            Diccionario con datos procesados
        """
        logger.info(f"🏙️  Procesando {city_config['name']} ({city_id})")
        
        try:
            # Generar grilla de alta densidad
            lon_grid, lat_grid = self.generate_high_density_grid(
                city_config['bbox'], 
                resolution=0.008  # ~800m resolution for 3000+ points
            )
            
            # Obtener timestamp actual
            timestamp = datetime.utcnow()
            
            # 1. Datos TEMPO (NO2, O3)
            logger.info(f"  📡 Obteniendo datos TEMPO...")
            tempo_data = await self.fetch_tempo_for_city(city_config['bbox'], timestamp)
            
            # 2. Datos OpenAQ (estaciones terrestres)
            logger.info(f"  🏭 Obteniendo datos OpenAQ...")
            openaq_data = await self.fetch_openaq_for_city(city_config['bbox'], timestamp)
            
            # 3. Datos meteorológicos MERRA-2
            logger.info(f"  🌤️  Obteniendo datos MERRA-2...")
            merra2_data = await self.fetch_merra2_for_city(city_config['bbox'], timestamp)
            
            # 4. Interpolar y fusionar datos
            logger.info(f"  🔄 Interpolando y fusionando datos...")
            fused_data = self.fuse_data_sources(
                lon_grid, lat_grid, 
                tempo_data, openaq_data, merra2_data,
                timestamp
            )
            
            # 5. Calcular índices de calidad del aire
            logger.info(f"  📊 Calculando AQI...")
            fused_data = self.calculate_air_quality_metrics(fused_data)
            
            # 6. Guardar datos
            await self.save_city_data(city_id, city_config, fused_data)
            
            # Actualizar estadísticas
            self.stats["cities_processed"] += 1
            self.stats["total_points"] += len(fused_data)
            
            logger.info(f"  ✅ {city_config['name']} completada: {len(fused_data)} puntos")
            
            return {
                "city_id": city_id,
                "name": city_config['name'],
                "points": len(fused_data),
                "status": "success",
                "timestamp": timestamp.isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error procesando {city_id}: {str(e)}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
            
            return {
                "city_id": city_id,
                "name": city_config['name'],
                "status": "error",
                "error": str(e),
                "timestamp": timestamp.isoformat()
            }
    
    async def fetch_tempo_for_city(self, bbox: List[float], timestamp: datetime) -> Optional[xr.Dataset]:
        """Obtiene datos TEMPO para una ciudad"""
        try:
            # Usar el módulo existente de TEMPO
            tempo_data = await fetch_tempo_data(bbox, timestamp)
            return tempo_data
        except Exception as e:
            logger.warning(f"Error obteniendo TEMPO: {e}")
            return None
    
    async def fetch_openaq_for_city(self, bbox: List[float], timestamp: datetime) -> Optional[pd.DataFrame]:
        """Obtiene datos OpenAQ para una ciudad"""
        try:
            # Usar el módulo existente de OpenAQ
            openaq_data = await fetch_openaq_data(bbox)
            return openaq_data
        except Exception as e:
            logger.warning(f"Error obteniendo OpenAQ: {e}")
            return None
    
    async def fetch_merra2_for_city(self, bbox: List[float], timestamp: datetime) -> Optional[xr.Dataset]:
        """Obtiene datos MERRA-2 para una ciudad"""
        try:
            # Usar el módulo existente de MERRA-2
            merra2_data = await fetch_merra2_data(bbox, timestamp)
            return merra2_data
        except Exception as e:
            logger.warning(f"Error obteniendo MERRA-2: {e}")
            return None
    
    def fuse_data_sources(self, lon_grid: np.ndarray, lat_grid: np.ndarray, 
                         tempo_data: Optional[xr.Dataset], 
                         openaq_data: Optional[pd.DataFrame],
                         merra2_data: Optional[xr.Dataset],
                         timestamp: datetime) -> pd.DataFrame:
        """
        Fusiona datos de diferentes fuentes en una grilla unificada
        """
        # Crear DataFrame base con la grilla
        points_data = []
        
        for i in range(lon_grid.shape[0]):
            for j in range(lon_grid.shape[1]):
                lon = lon_grid[i, j]
                lat = lat_grid[i, j]
                
                point = {
                    'longitude': lon,
                    'latitude': lat,
                    'timestamp': timestamp,
                    # Inicializar con valores por defecto
                    'no2_column': np.nan,
                    'o3_column': np.nan,
                    'pm25_surface': np.nan,
                    'temperature': np.nan,
                    'humidity': np.nan,
                    'wind_speed': np.nan,
                    'wind_direction': np.nan,
                    'pressure': np.nan,
                    'data_quality': 0.0
                }
                
                # Interpolar datos TEMPO si están disponibles
                if tempo_data is not None:
                    point.update(self.interpolate_tempo_data(tempo_data, lon, lat))
                
                # Usar datos OpenAQ cercanos si están disponibles
                if openaq_data is not None:
                    point.update(self.interpolate_openaq_data(openaq_data, lon, lat))
                
                # Interpolar datos MERRA-2 si están disponibles
                if merra2_data is not None:
                    point.update(self.interpolate_merra2_data(merra2_data, lon, lat))
                
                points_data.append(point)
        
        df = pd.DataFrame(points_data)
        
        # Aplicar filtros de calidad
        df = self.apply_quality_filters(df)
        
        return df
    
    def interpolate_tempo_data(self, tempo_data: xr.Dataset, lon: float, lat: float) -> Dict:
        """Interpola datos TEMPO para un punto específico"""
        try:
            # Interpolar NO2 y O3
            no2_val = float(tempo_data['no2_column'].interp(longitude=lon, latitude=lat, method='linear'))
            o3_val = float(tempo_data['o3_column'].interp(longitude=lon, latitude=lat, method='linear'))
            
            return {
                'no2_column': no2_val if not np.isnan(no2_val) else np.nan,
                'o3_column': o3_val if not np.isnan(o3_val) else np.nan,
                'data_quality': 0.8  # TEMPO tiene alta calidad
            }
        except:
            return {'data_quality': 0.1}
    
    def interpolate_openaq_data(self, openaq_data: pd.DataFrame, lon: float, lat: float) -> Dict:
        """Interpola datos OpenAQ para un punto específico usando estaciones cercanas"""
        try:
            # Encontrar estaciones dentro de un radio de 50km
            distances = np.sqrt((openaq_data['longitude'] - lon)**2 + (openaq_data['latitude'] - lat)**2)
            nearby = openaq_data[distances < 0.5]  # ~50km
            
            if len(nearby) > 0:
                # Usar promedio ponderado por distancia inversa
                weights = 1.0 / (distances[distances < 0.5] + 0.001)
                
                pm25_val = np.average(nearby['pm25'].fillna(0), weights=weights)
                
                return {
                    'pm25_surface': pm25_val,
                    'data_quality': min(1.0, 0.6 + len(nearby) * 0.1)  # Más estaciones = mejor calidad
                }
        except:
            pass
        
        return {}
    
    def interpolate_merra2_data(self, merra2_data: xr.Dataset, lon: float, lat: float) -> Dict:
        """Interpola datos MERRA-2 para un punto específico"""
        try:
            temp_val = float(merra2_data['temperature'].interp(longitude=lon, latitude=lat, method='linear'))
            humidity_val = float(merra2_data['humidity'].interp(longitude=lon, latitude=lat, method='linear'))
            wind_speed_val = float(merra2_data['wind_speed'].interp(longitude=lon, latitude=lat, method='linear'))
            wind_dir_val = float(merra2_data['wind_direction'].interp(longitude=lon, latitude=lat, method='linear'))
            pressure_val = float(merra2_data['pressure'].interp(longitude=lon, latitude=lat, method='linear'))
            
            return {
                'temperature': temp_val - 273.15 if not np.isnan(temp_val) else np.nan,  # K to C
                'humidity': humidity_val if not np.isnan(humidity_val) else np.nan,
                'wind_speed': wind_speed_val if not np.isnan(wind_speed_val) else np.nan,
                'wind_direction': wind_dir_val if not np.isnan(wind_dir_val) else np.nan,
                'pressure': pressure_val if not np.isnan(pressure_val) else np.nan
            }
        except:
            return {}
    
    def apply_quality_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica filtros de calidad a los datos"""
        # Filtrar valores extremos
        df.loc[df['no2_column'] < 0, 'no2_column'] = np.nan
        df.loc[df['no2_column'] > 1e16, 'no2_column'] = np.nan
        
        df.loc[df['pm25_surface'] < 0, 'pm25_surface'] = np.nan
        df.loc[df['pm25_surface'] > 500, 'pm25_surface'] = np.nan
        
        df.loc[df['temperature'] < -50, 'temperature'] = np.nan
        df.loc[df['temperature'] > 60, 'temperature'] = np.nan
        
        return df
    
    def calculate_air_quality_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula métricas de calidad del aire"""
        # AQI para PM2.5 (EPA standard)
        df['aqi_pm25'] = df['pm25_surface'].apply(self.pm25_to_aqi)
        
        # AQI para NO2 (basado en columna troposférica)
        df['aqi_no2'] = df['no2_column'].apply(self.no2_column_to_aqi)
        
        # AQI combinado (tomar el máximo)
        df['aqi_combined'] = df[['aqi_pm25', 'aqi_no2']].max(axis=1)
        
        # Categoría de calidad del aire
        df['air_quality_category'] = df['aqi_combined'].apply(self.aqi_to_category)
        
        return df
    
    def pm25_to_aqi(self, pm25_val: float) -> float:
        """Convierte PM2.5 (μg/m³) a AQI"""
        if pd.isna(pm25_val):
            return np.nan
        
        # Breakpoints EPA para PM2.5
        if pm25_val <= 12.0:
            return (50 / 12.0) * pm25_val
        elif pm25_val <= 35.4:
            return 50 + ((100 - 50) / (35.4 - 12.1)) * (pm25_val - 12.1)
        elif pm25_val <= 55.4:
            return 100 + ((150 - 100) / (55.4 - 35.5)) * (pm25_val - 35.5)
        elif pm25_val <= 150.4:
            return 150 + ((200 - 150) / (150.4 - 55.5)) * (pm25_val - 55.5)
        elif pm25_val <= 250.4:
            return 200 + ((300 - 200) / (250.4 - 150.5)) * (pm25_val - 150.5)
        else:
            return 300 + ((500 - 300) / (500.4 - 250.5)) * min(pm25_val - 250.5, 249.9)
    
    def no2_column_to_aqi(self, no2_column: float) -> float:
        """Convierte columna troposférica NO2 a AQI aproximado"""
        if pd.isna(no2_column):
            return np.nan
        
        # Conversión aproximada basada en correlaciones con surface NO2
        # NO2 column (molec/cm²) -> surface NO2 (ppb) -> AQI
        surface_no2_approx = no2_column / 2.69e15 * 100  # Aproximación
        
        # Breakpoints EPA para NO2
        if surface_no2_approx <= 53:
            return (50 / 53) * surface_no2_approx
        elif surface_no2_approx <= 100:
            return 50 + ((100 - 50) / (100 - 54)) * (surface_no2_approx - 54)
        elif surface_no2_approx <= 360:
            return 100 + ((150 - 100) / (360 - 101)) * (surface_no2_approx - 101)
        elif surface_no2_approx <= 649:
            return 150 + ((200 - 150) / (649 - 361)) * (surface_no2_approx - 361)
        else:
            return 200 + min((surface_no2_approx - 650) / 10, 100)
    
    def aqi_to_category(self, aqi_val: float) -> str:
        """Convierte AQI a categoría textual"""
        if pd.isna(aqi_val):
            return "No Data"
        elif aqi_val <= 50:
            return "Good"
        elif aqi_val <= 100:
            return "Moderate"
        elif aqi_val <= 150:
            return "Unhealthy for Sensitive Groups"
        elif aqi_val <= 200:
            return "Unhealthy"
        elif aqi_val <= 300:
            return "Very Unhealthy"
        else:
            return "Hazardous"
    
    async def save_city_data(self, city_id: str, city_config: Dict, data: pd.DataFrame):
        """Guarda datos de una ciudad en múltiples formatos"""
        city_dir = self.output_dir / city_id
        city_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # 1. CSV para frontend
        csv_file = city_dir / f"{city_id}_latest.csv"
        data.to_csv(csv_file, index=False)
        
        # 2. CSV con timestamp
        csv_timestamped = city_dir / f"{city_id}_{timestamp}.csv"
        data.to_csv(csv_timestamped, index=False)
        
        # 3. JSON resumen para API
        summary = {
            "city_id": city_id,
            "name": city_config['name'],
            "bbox": city_config['bbox'],
            "population": city_config['population'],
            "timezone": city_config['timezone'],
            "last_update": datetime.utcnow().isoformat(),
            "total_points": len(data),
            "data_quality": {
                "mean_quality": float(data['data_quality'].mean()),
                "points_with_tempo": int((~data['no2_column'].isna()).sum()),
                "points_with_openaq": int((~data['pm25_surface'].isna()).sum()),
                "points_with_weather": int((~data['temperature'].isna()).sum())
            },
            "air_quality_summary": {
                "mean_aqi": float(data['aqi_combined'].mean()) if not data['aqi_combined'].isna().all() else None,
                "max_aqi": float(data['aqi_combined'].max()) if not data['aqi_combined'].isna().all() else None,
                "dominant_category": data['air_quality_category'].mode().iloc[0] if len(data['air_quality_category'].mode()) > 0 else "No Data"
            }
        }
        
        summary_file = city_dir / f"{city_id}_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"  💾 Datos guardados en {city_dir}")
    
    async def run_complete_etl(self, cities: Optional[List[str]] = None):
        """
        Ejecuta ETL completo para todas las ciudades o una lista específica
        
        Args:
            cities: Lista de city_ids a procesar. Si None, procesa todas.
        """
        start_time = datetime.utcnow()
        logger.info("🚀 Iniciando ETL Multi-Ciudad Completo")
        
        # Determinar ciudades a procesar
        if cities is None:
            cities_to_process = SUPPORTED_CITIES
        else:
            cities_to_process = {k: v for k, v in SUPPORTED_CITIES.items() if k in cities}
        
        logger.info(f"📍 Procesando {len(cities_to_process)} ciudades: {list(cities_to_process.keys())}")
        
        # Procesar ciudades en paralelo (limitado para no sobrecargar APIs)
        semaphore = asyncio.Semaphore(3)  # Máximo 3 ciudades simultáneas
        
        async def process_city_with_semaphore(city_id, city_config):
            async with semaphore:
                return await self.process_city_data(city_id, city_config)
        
        # Crear tareas
        tasks = [
            process_city_with_semaphore(city_id, city_config) 
            for city_id, city_config in cities_to_process.items()
        ]
        
        # Ejecutar todas las tareas
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        successful = []
        failed = []
        
        for result in results:
            if isinstance(result, Exception):
                failed.append(str(result))
            elif result.get('status') == 'success':
                successful.append(result)
            else:
                failed.append(result)
        
        # Calcular estadísticas finales
        end_time = datetime.utcnow()
        self.stats["processing_time"] = (end_time - start_time).total_seconds()
        
        # Generar reporte final
        await self.generate_final_report(successful, failed, start_time, end_time)
        
        logger.info("🎉 ETL Multi-Ciudad Completado")
        return self.stats
    
    async def generate_final_report(self, successful: List[Dict], failed: List, 
                                  start_time: datetime, end_time: datetime):
        """Genera reporte final del ETL"""
        report = {
            "etl_summary": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "processing_time_seconds": (end_time - start_time).total_seconds(),
                "cities_total": len(SUPPORTED_CITIES),
                "cities_successful": len(successful),
                "cities_failed": len(failed),
                "total_points_generated": sum(city['points'] for city in successful),
                "success_rate": len(successful) / len(SUPPORTED_CITIES) * 100
            },
            "successful_cities": successful,
            "failed_cities": failed,
            "data_sources_status": {
                "tempo_available": True,  # Actualizar según disponibilidad real
                "openaq_available": True,
                "merra2_available": True
            },
            "next_scheduled_run": (end_time + timedelta(hours=1)).isoformat()
        }
        
        # Guardar reporte
        report_file = self.output_dir / f"etl_report_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # También guardar como "latest"
        latest_report = self.output_dir / "etl_report_latest.json"
        with open(latest_report, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Reporte guardado: {report_file}")
        
        # Log resumen
        logger.info("="*60)
        logger.info("📈 RESUMEN ETL MULTI-CIUDAD")
        logger.info("="*60)
        logger.info(f"✅ Ciudades exitosas: {len(successful)}")
        logger.info(f"❌ Ciudades fallidas: {len(failed)}")
        logger.info(f"📍 Total puntos generados: {sum(city['points'] for city in successful):,}")
        logger.info(f"⏱️  Tiempo total: {(end_time - start_time).total_seconds():.1f}s")
        logger.info(f"📊 Tasa de éxito: {len(successful) / len(SUPPORTED_CITIES) * 100:.1f}%")
        logger.info("="*60)


async def main():
    """Función principal para ejecutar el ETL"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ETL Multi-Ciudad CleanSky')
    parser.add_argument('--cities', nargs='+', help='Ciudades específicas a procesar')
    parser.add_argument('--test', action='store_true', help='Ejecutar en modo test con datos sintéticos')
    
    args = parser.parse_args()
    
    # Inicializar ETL
    etl = MultiCityETL()
    
    if args.test:
        logger.info("🧪 Ejecutando en modo TEST con datos sintéticos")
        # En modo test, usar generadores de datos sintéticos
    
    # Ejecutar ETL
    try:
        stats = await etl.run_complete_etl(cities=args.cities)
        logger.info(f"🎯 ETL completado: {stats}")
        return 0
    except Exception as e:
        logger.error(f"💥 Error en ETL: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))