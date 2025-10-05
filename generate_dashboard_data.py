#!/usr/bin/env python3
"""
Generador de Datos de Muestra para Dashboard CleanSky
Crea datos sintéticos que se ven bien en el dashboard
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys
import logging

# Agregar directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from config_multicity import SUPPORTED_CITIES

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardSampleDataGenerator:
    """Generador de datos de muestra específicos para el dashboard"""
    
    def __init__(self):
        self.output_dir = Path("data/multi_city_processed")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Configuración de datos realistas por ciudad
        self.city_characteristics = {
            "los_angeles": {
                "base_pollution": 65,  # Higher pollution (traffic + industry)
                "variability": 25,
                "hotspots": [(34.0522, -118.2437), (34.0928, -118.3287)],  # Downtown, Hollywood
                "description": "Alta contaminación por tráfico"
            },
            "new_york": {
                "base_pollution": 55,
                "variability": 20,
                "hotspots": [(40.7589, -73.9851), (40.6892, -74.0445)],  # Manhattan, Jersey City
                "description": "Contaminación urbana moderada-alta"
            },
            "chicago": {
                "base_pollution": 45,
                "variability": 18,
                "hotspots": [(41.8781, -87.6298), (41.8369, -87.6847)],  # Downtown, West Side
                "description": "Contaminación urbana moderada"
            },
            "houston": {
                "base_pollution": 60,
                "variability": 22,
                "hotspots": [(29.7604, -95.3698), (29.7372, -95.4618)],  # Downtown, Refineries
                "description": "Alta contaminación industrial"
            },
            "phoenix": {
                "base_pollution": 50,
                "variability": 20,
                "hotspots": [(33.4484, -112.0740), (33.5206, -112.2640)],  # Phoenix, Glendale
                "description": "Contaminación moderada (calor + tráfico)"
            },
            "seattle": {
                "base_pollution": 35,
                "variability": 15,
                "hotspots": [(47.6062, -122.3321), (47.5480, -122.3040)],  # Downtown, Georgetown
                "description": "Baja contaminación (clima húmedo)"
            },
            "miami": {
                "base_pollution": 40,
                "variability": 16,
                "hotspots": [(25.7617, -80.1918), (25.7907, -80.1300)],  # Downtown, Miami Beach
                "description": "Contaminación baja-moderada"
            },
            "denver": {
                "base_pollution": 48,
                "variability": 20,
                "hotspots": [(39.7392, -104.9903), (39.7767, -105.0178)],  # Downtown, Highlands
                "description": "Contaminación moderada (altitud)"
            },
            "boston": {
                "base_pollution": 42,
                "variability": 17,
                "hotspots": [(42.3601, -71.0589), (42.3188, -71.0846)],  # Downtown, South End
                "description": "Contaminación baja-moderada"
            },
            "atlanta": {
                "base_pollution": 52,
                "variability": 19,
                "hotspots": [(33.7490, -84.3880), (33.7756, -84.3963)],  # Downtown, Midtown
                "description": "Contaminación moderada"
            }
        }
    
    async def generate_all_cities_data(self, points_per_city: int = 3000):
        """Genera datos para todas las ciudades"""
        logger.info(f"🎲 Generando datos de muestra para {len(SUPPORTED_CITIES)} ciudades")
        logger.info(f"📊 {points_per_city} puntos por ciudad = {points_per_city * len(SUPPORTED_CITIES):,} puntos totales")
        
        for city_id, city_config in SUPPORTED_CITIES.items():
            logger.info(f"🏙️  Generando {city_id}...")
            await self.generate_city_data(city_id, city_config, points_per_city)
        
        # Generar reporte final
        await self.generate_summary_report()
        
        logger.info("🎉 Generación de datos completada")
    
    async def generate_city_data(self, city_id: str, city_config: dict, num_points: int):
        """Genera datos realistas para una ciudad específica"""
        
        # Crear directorio de ciudad
        city_dir = self.output_dir / city_id
        city_dir.mkdir(exist_ok=True)
        
        # Obtener características de la ciudad
        characteristics = self.city_characteristics.get(city_id, {
            "base_pollution": 50,
            "variability": 20,
            "hotspots": [],
            "description": "Contaminación estándar"
        })
        
        # Generar grilla de puntos
        bbox = city_config["bbox"]
        west, south, east, north = bbox
        
        # Crear grilla uniforme con algo de variación
        grid_points = self.create_realistic_grid(bbox, num_points)
        
        # Generar datos para cada punto
        data_points = []
        
        for i, (lon, lat) in enumerate(grid_points):
            # Calcular distancia a hotspots para variación espacial
            pollution_factor = self.calculate_pollution_factor(
                lon, lat, characteristics["hotspots"], characteristics["base_pollution"]
            )
            
            # Generar datos realistas
            point_data = self.generate_point_data(
                lon, lat, pollution_factor, characteristics["variability"]
            )
            
            data_points.append(point_data)
        
        # Crear DataFrame
        df = pd.DataFrame(data_points)
        
        # Guardar archivos
        await self.save_city_data(city_id, city_config, df, characteristics)
        
        logger.info(f"  ✅ {city_config['name']}: {len(df)} puntos generados")
    
    def create_realistic_grid(self, bbox: list, num_points: int) -> list:
        """Crea una grilla realista con distribución no uniforme"""
        west, south, east, north = bbox
        
        # Calcular densidad aproximada
        area_width = east - west
        area_height = north - south
        
        # Distribución más densa en el centro (área urbana)
        points = []
        
        # Grid base uniforme
        grid_size = int(np.sqrt(num_points * 0.7))  # 70% uniforme
        
        lon_step = area_width / grid_size
        lat_step = area_height / grid_size
        
        # Puntos uniformes
        for i in range(grid_size):
            for j in range(grid_size):
                lon = west + (i + 0.5) * lon_step + np.random.normal(0, lon_step * 0.1)
                lat = south + (j + 0.5) * lat_step + np.random.normal(0, lat_step * 0.1)
                
                # Mantener dentro de bounds
                lon = max(west, min(east, lon))
                lat = max(south, min(north, lat))
                
                points.append((lon, lat))
        
        # Puntos adicionales aleatorios (30%)
        remaining_points = num_points - len(points)
        
        for _ in range(remaining_points):
            lon = np.random.uniform(west, east)
            lat = np.random.uniform(south, north)
            points.append((lon, lat))
        
        return points[:num_points]
    
    def calculate_pollution_factor(self, lon: float, lat: float, hotspots: list, base_pollution: float) -> float:
        """Calcula factor de contaminación basado en distancia a hotspots"""
        
        if not hotspots:
            return base_pollution
        
        # Calcular distancia mínima a hotspots
        min_distance = float('inf')
        
        for hotspot_lat, hotspot_lon in hotspots:
            distance = np.sqrt((lon - hotspot_lon)**2 + (lat - hotspot_lat)**2)
            min_distance = min(min_distance, distance)
        
        # Factor de distancia (más cerca = más contaminación)
        distance_factor = np.exp(-min_distance * 50)  # Decay exponencial
        
        # Pollution aumenta cerca de hotspots
        pollution_boost = distance_factor * 30
        
        return base_pollution + pollution_boost
    
    def generate_point_data(self, lon: float, lat: float, pollution_factor: float, variability: float) -> dict:
        """Genera datos realistas para un punto específico"""
        
        # Timestamp actual
        timestamp = datetime.utcnow()
        
        # Risk score basado en pollution factor con variabilidad
        risk_score = pollution_factor + np.random.normal(0, variability)
        risk_score = max(0, min(100, risk_score))  # Clamp 0-100
        
        # NO2 columnar (correlacionado con risk score)
        no2_base = (risk_score / 100) * 8e15  # Rango típico TEMPO
        no2_column = no2_base * (1 + np.random.normal(0, 0.3))
        no2_column = max(1e14, no2_column)  # Mínimo realista
        
        # PM2.5 superficial (correlacionado pero con más variabilidad)
        pm25_base = (risk_score / 100) * 40  # 0-40 μg/m³
        pm25_surface = pm25_base * (1 + np.random.normal(0, 0.4))
        pm25_surface = max(0, pm25_surface)
        
        # O3 (anti-correlacionado parcialmente con NO2)
        o3_base = (80 - risk_score * 0.3) / 100 * 6e15
        o3_column = o3_base * (1 + np.random.normal(0, 0.2))
        o3_column = max(1e14, o3_column)
        
        # Datos meteorológicos
        temperature = np.random.normal(20, 8)  # °C
        humidity = np.random.normal(60, 15)    # %
        humidity = max(20, min(90, humidity))
        
        wind_speed = np.random.exponential(3)  # m/s
        wind_direction = np.random.uniform(0, 360)  # grados
        
        pressure = np.random.normal(1013, 10)  # hPa
        
        # Calidad de datos (simulada)
        data_quality = np.random.uniform(0.7, 1.0)
        
        # AQI calculado
        aqi_pm25 = self.pm25_to_aqi(pm25_surface)
        aqi_no2 = self.no2_column_to_aqi(no2_column)
        aqi_combined = max(aqi_pm25, aqi_no2)
        
        # Categoría de calidad del aire
        air_quality_category = self.aqi_to_category(aqi_combined)
        
        return {
            'longitude': round(lon, 6),
            'latitude': round(lat, 6),
            'timestamp': timestamp,
            'no2_column': no2_column,
            'o3_column': o3_column,
            'pm25_surface': pm25_surface,
            'temperature': temperature,
            'humidity': humidity,
            'wind_speed': wind_speed,
            'wind_direction': wind_direction,
            'pressure': pressure,
            'data_quality': data_quality,
            'aqi_pm25': aqi_pm25,
            'aqi_no2': aqi_no2,
            'aqi_combined': aqi_combined,
            'air_quality_category': air_quality_category,
            'risk_score': risk_score  # Para compatibilidad con dashboard
        }
    
    def pm25_to_aqi(self, pm25_val: float) -> float:
        """Convierte PM2.5 a AQI (EPA)"""
        if pm25_val <= 12.0:
            return (50 / 12.0) * pm25_val
        elif pm25_val <= 35.4:
            return 50 + ((100 - 50) / (35.4 - 12.1)) * (pm25_val - 12.1)
        elif pm25_val <= 55.4:
            return 100 + ((150 - 100) / (55.4 - 35.5)) * (pm25_val - 35.5)
        elif pm25_val <= 150.4:
            return 150 + ((200 - 150) / (150.4 - 55.5)) * (pm25_val - 55.5)
        else:
            return min(300, 200 + ((300 - 200) / (250.4 - 150.5)) * (pm25_val - 150.5))
    
    def no2_column_to_aqi(self, no2_column: float) -> float:
        """Convierte NO2 columnar a AQI aproximado"""
        # Conversión aproximada columna troposférica -> superficie -> AQI
        surface_no2_approx = no2_column / 2.69e15 * 100
        
        if surface_no2_approx <= 53:
            return (50 / 53) * surface_no2_approx
        elif surface_no2_approx <= 100:
            return 50 + ((100 - 50) / (100 - 54)) * (surface_no2_approx - 54)
        else:
            return min(200, 100 + ((150 - 100) / (360 - 101)) * (surface_no2_approx - 101))
    
    def aqi_to_category(self, aqi_val: float) -> str:
        """Convierte AQI a categoría"""
        if aqi_val <= 50:
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
    
    async def save_city_data(self, city_id: str, city_config: dict, df: pd.DataFrame, characteristics: dict):
        """Guarda datos de ciudad en múltiples formatos"""
        
        city_dir = self.output_dir / city_id
        
        # CSV principal
        csv_file = city_dir / f"{city_id}_latest.csv"
        df.to_csv(csv_file, index=False)
        
        # Resumen JSON
        summary = {
            "city_id": city_id,
            "name": city_config["name"],
            "bbox": city_config["bbox"],
            "population": city_config["population"],
            "timezone": city_config["timezone"],
            "last_update": datetime.utcnow().isoformat(),
            "total_points": len(df),
            "characteristics": characteristics,
            "data_quality": {
                "mean_quality": float(df['data_quality'].mean()),
                "points_high_quality": int((df['data_quality'] > 0.8).sum()),
                "coverage_percentage": 100.0
            },
            "air_quality_summary": {
                "mean_aqi": float(df['aqi_combined'].mean()),
                "max_aqi": float(df['aqi_combined'].max()),
                "min_aqi": float(df['aqi_combined'].min()),
                "dominant_category": df['air_quality_category'].mode().iloc[0]
            },
            "pollutant_stats": {
                "mean_no2": float(df['no2_column'].mean()),
                "mean_pm25": float(df['pm25_surface'].mean()),
                "mean_temperature": float(df['temperature'].mean())
            }
        }
        
        summary_file = city_dir / f"{city_id}_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
    
    async def generate_summary_report(self):
        """Genera reporte resumen de todos los datos generados"""
        
        report = {
            "generation_summary": {
                "timestamp": datetime.utcnow().isoformat(),
                "total_cities": len(SUPPORTED_CITIES),
                "data_type": "synthetic_sample",
                "optimized_for": "CleanSky Dashboard"
            },
            "cities": {},
            "global_stats": {
                "total_points": 0,
                "average_aqi": 0,
                "cities_by_risk": {
                    "low": [],
                    "moderate": [],
                    "high": [],
                    "very_high": []
                }
            }
        }
        
        total_aqi = 0
        
        for city_id in SUPPORTED_CITIES.keys():
            summary_file = self.output_dir / city_id / f"{city_id}_summary.json"
            
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    city_summary = json.load(f)
                
                report["cities"][city_id] = city_summary
                report["global_stats"]["total_points"] += city_summary["total_points"]
                
                city_aqi = city_summary["air_quality_summary"]["mean_aqi"]
                total_aqi += city_aqi
                
                # Clasificar ciudad por riesgo
                if city_aqi <= 50:
                    report["global_stats"]["cities_by_risk"]["low"].append(city_id)
                elif city_aqi <= 100:
                    report["global_stats"]["cities_by_risk"]["moderate"].append(city_id)
                elif city_aqi <= 150:
                    report["global_stats"]["cities_by_risk"]["high"].append(city_id)
                else:
                    report["global_stats"]["cities_by_risk"]["very_high"].append(city_id)
        
        # Calcular AQI promedio
        if len(SUPPORTED_CITIES) > 0:
            report["global_stats"]["average_aqi"] = total_aqi / len(SUPPORTED_CITIES)
        
        # Guardar reporte
        report_file = self.output_dir / "dashboard_sample_data_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Reporte guardado: {report_file}")
        logger.info(f"📈 Total puntos: {report['global_stats']['total_points']:,}")
        logger.info(f"🎯 AQI promedio: {report['global_stats']['average_aqi']:.1f}")


async def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generar datos de muestra para dashboard')
    parser.add_argument('--points', type=int, default=3000, help='Puntos por ciudad')
    parser.add_argument('--cities', nargs='+', help='Ciudades específicas')
    
    args = parser.parse_args()
    
    generator = DashboardSampleDataGenerator()
    
    if args.cities:
        # Solo ciudades específicas
        for city_id in args.cities:
            if city_id in SUPPORTED_CITIES:
                city_config = SUPPORTED_CITIES[city_id]
                await generator.generate_city_data(city_id, city_config, args.points)
            else:
                logger.error(f"Ciudad no soportada: {city_id}")
    else:
        # Todas las ciudades
        await generator.generate_all_cities_data(args.points)


if __name__ == "__main__":
    asyncio.run(main())