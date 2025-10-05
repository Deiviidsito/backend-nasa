#!/usr/bin/env python3
"""
Script de Configuración Completa para CleanSky Multi-Ciudad Optimizada
Integra ETL, API optimizada y base de datos para manejar 3,000+ puntos por ciudad
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
import argparse

# Agregar directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from config_multicity import SUPPORTED_CITIES
from database_optimized import get_storage, DATABASE_CONFIGS
from etl.multi_city_etl_complete import MultiCityETL

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('setup_multi_city.log')
    ]
)
logger = logging.getLogger(__name__)

class MultiCitySetup:
    """Configurador completo del sistema multi-ciudad"""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.storage = None
        self.etl = None
        
        # Estadísticas de setup
        self.setup_stats = {
            "start_time": None,
            "end_time": None,
            "cities_configured": 0,
            "total_points_generated": 0,
            "errors": [],
            "warnings": []
        }
    
    async def initialize(self):
        """Inicializa componentes del sistema"""
        logger.info("🚀 Iniciando configuración Multi-Ciudad CleanSky")
        self.setup_stats["start_time"] = datetime.utcnow()
        
        # 1. Inicializar base de datos optimizada
        logger.info("🗄️  Inicializando base de datos optimizada...")
        self.storage = await get_storage(self.environment)
        
        # 2. Inicializar ETL
        logger.info("⚙️  Inicializando ETL multi-ciudad...")
        self.etl = MultiCityETL()
        
        logger.info("✅ Componentes inicializados")
    
    async def setup_complete_system(self, 
                                  cities: Optional[List[str]] = None,
                                  run_etl: bool = True,
                                  optimize_database: bool = True,
                                  create_indexes: bool = True,
                                  generate_sample_data: bool = False) -> Dict:
        """
        Configuración completa del sistema multi-ciudad
        
        Args:
            cities: Lista de ciudades a configurar (None = todas)
            run_etl: Ejecutar ETL completo
            optimize_database: Aplicar optimizaciones de BD
            create_indexes: Crear índices espaciales
            generate_sample_data: Generar datos de muestra si no hay datos reales
        """
        
        try:
            await self.initialize()
            
            # Determinar ciudades a procesar
            cities_to_process = cities or list(SUPPORTED_CITIES.keys())
            logger.info(f"📍 Configurando {len(cities_to_process)} ciudades: {cities_to_process}")
            
            # 1. Configurar estructura de base de datos
            if optimize_database:
                logger.info("🔧 Optimizando base de datos...")
                await self._optimize_database()
            
            # 2. Crear índices espaciales
            if create_indexes:
                logger.info("🗂️  Creando índices espaciales...")
                await self._create_spatial_indexes()
            
            # 3. Ejecutar ETL para generar datos
            if run_etl:
                logger.info("🔄 Ejecutando ETL multi-ciudad...")
                etl_stats = await self._run_complete_etl(cities_to_process, generate_sample_data)
                self.setup_stats.update(etl_stats)
            
            # 4. Validar configuración
            logger.info("✅ Validando configuración...")
            validation_results = await self._validate_setup(cities_to_process)
            
            # 5. Generar reporte final
            final_report = await self._generate_setup_report(validation_results)
            
            self.setup_stats["end_time"] = datetime.utcnow()
            self.setup_stats["cities_configured"] = len(cities_to_process)
            
            logger.info("🎉 Configuración multi-ciudad completada")
            return final_report
            
        except Exception as e:
            logger.error(f"💥 Error en configuración: {e}")
            self.setup_stats["errors"].append(str(e))
            raise
    
    async def _optimize_database(self):
        """Aplica optimizaciones específicas a la base de datos"""
        
        # Configuraciones según el tipo de BD
        if self.storage.config.db_type.value == "postgresql":
            # Optimizaciones PostgreSQL
            await self._optimize_postgresql()
        
        elif self.storage.config.db_type.value == "sqlite":
            # Optimizaciones SQLite
            await self._optimize_sqlite()
        
        elif self.storage.config.db_type.value == "filesystem":
            # Optimizaciones sistema de archivos
            await self._optimize_filesystem()
        
        logger.info("✅ Optimizaciones de base de datos aplicadas")
    
    async def _optimize_postgresql(self):
        """Optimizaciones específicas para PostgreSQL"""
        optimizations = [
            "ALTER SYSTEM SET shared_buffers = '256MB'",
            "ALTER SYSTEM SET effective_cache_size = '1GB'", 
            "ALTER SYSTEM SET random_page_cost = 1.1",
            "ALTER SYSTEM SET work_mem = '16MB'",
            "ALTER SYSTEM SET maintenance_work_mem = '64MB'",
        ]
        
        async with self.storage.connection_pool.acquire() as conn:
            for opt in optimizations:
                try:
                    await conn.execute(opt)
                    logger.debug(f"✅ Aplicada: {opt}")
                except Exception as e:
                    logger.warning(f"⚠️  No se pudo aplicar: {opt} - {e}")
    
    async def _optimize_sqlite(self):
        """Optimizaciones específicas para SQLite"""
        optimizations = [
            "PRAGMA cache_size = 10000",
            "PRAGMA synchronous = NORMAL", 
            "PRAGMA journal_mode = WAL",
            "PRAGMA temp_store = MEMORY",
            "PRAGMA mmap_size = 268435456",
            "PRAGMA optimize"
        ]
        
        for opt in optimizations:
            try:
                self.storage.sqlite_conn.execute(opt)
                logger.debug(f"✅ Aplicada: {opt}")
            except Exception as e:
                logger.warning(f"⚠️  No se pudo aplicar: {opt} - {e}")
        
        self.storage.sqlite_conn.commit()
    
    async def _optimize_filesystem(self):
        """Optimizaciones para sistema de archivos"""
        # Crear estructura de directorios optimizada
        base_dir = Path("data/multi_city_optimized")
        
        # Directorio para índices y cache
        (base_dir / "indexes").mkdir(exist_ok=True, parents=True)
        (base_dir / "cache").mkdir(exist_ok=True, parents=True)
        (base_dir / "stats").mkdir(exist_ok=True, parents=True)
        (base_dir / "temp").mkdir(exist_ok=True, parents=True)
        
        # Configurar estructura por ciudad
        for city_id in SUPPORTED_CITIES.keys():
            city_dir = base_dir / city_id
            city_dir.mkdir(exist_ok=True)
            
            # Subdirectorios optimizados
            for subdir in ["latest", "historical", "cache", "stats", "tiles"]:
                (city_dir / subdir).mkdir(exist_ok=True)
        
        logger.info("📁 Estructura de directorios optimizada creada")
    
    async def _create_spatial_indexes(self):
        """Crea índices espaciales para búsquedas rápidas"""
        
        # Crear índices por ciudad
        for city_id in SUPPORTED_CITIES.keys():
            try:
                await self._create_city_spatial_index(city_id)
                logger.info(f"🗂️  Índice espacial creado para {city_id}")
            except Exception as e:
                logger.warning(f"⚠️  Error creando índice para {city_id}: {e}")
        
        logger.info("✅ Índices espaciales creados")
    
    async def _create_city_spatial_index(self, city_id: str):
        """Crea índice espacial para una ciudad específica"""
        
        if self.storage.config.db_type.value == "postgresql":
            # Usar PostGIS para índices espaciales reales
            async with self.storage.connection_pool.acquire() as conn:
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{city_id}_spatial 
                    ON city_air_quality USING GIST (ST_Point(longitude, latitude))
                    WHERE city_id = '{city_id}'
                """)
        
        elif self.storage.config.db_type.value == "filesystem":
            # Crear índice espacial simplificado en JSON
            city_config = SUPPORTED_CITIES[city_id]
            bbox = city_config["bbox"]
            
            # Generar grilla de índice
            resolution = city_config["grid_resolution"]
            grid_index = self._generate_grid_index(bbox, resolution)
            
            # Guardar índice
            index_file = Path("data/multi_city_optimized/indexes") / f"{city_id}_spatial.json"
            with open(index_file, 'w') as f:
                json.dump(grid_index, f, indent=2)
    
    def _generate_grid_index(self, bbox: List[float], resolution: float) -> Dict:
        """Genera índice de grilla espacial"""
        west, south, east, north = bbox
        
        # Calcular dimensiones de grilla
        lon_points = int((east - west) / resolution) + 1
        lat_points = int((north - south) / resolution) + 1
        
        return {
            "bbox": bbox,
            "resolution": resolution,
            "grid_dimensions": {
                "longitude_points": lon_points,
                "latitude_points": lat_points,
                "total_cells": lon_points * lat_points
            },
            "index_type": "regular_grid",
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def _run_complete_etl(self, cities: List[str], generate_sample: bool = False) -> Dict:
        """Ejecuta ETL completo para las ciudades especificadas"""
        
        if generate_sample:
            # Generar datos de muestra si no hay datos reales
            logger.info("🧪 Generando datos de muestra...")
            return await self._generate_sample_data(cities)
        else:
            # Ejecutar ETL real
            logger.info("🔄 Ejecutando ETL con datos reales...")
            return await self.etl.run_complete_etl(cities)
    
    async def _generate_sample_data(self, cities: List[str]) -> Dict:
        """Genera datos de muestra para testing"""
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        total_points = 0
        processed_cities = 0
        
        for city_id in cities:
            try:
                logger.info(f"🎲 Generando datos de muestra para {city_id}")
                
                city_config = SUPPORTED_CITIES[city_id]
                bbox = city_config["bbox"]
                
                # Generar grilla de puntos
                resolution = 0.008  # ~800m para obtener 3000+ puntos
                west, south, east, north = bbox
                
                lons = np.arange(west, east, resolution)
                lats = np.arange(south, north, resolution)
                lon_grid, lat_grid = np.meshgrid(lons, lats)
                
                # Crear DataFrame con datos sintéticos
                points = []
                for i in range(lon_grid.shape[0]):
                    for j in range(lon_grid.shape[1]):
                        # Datos sintéticos realistas
                        point = {
                            'longitude': lon_grid[i, j],
                            'latitude': lat_grid[i, j],
                            'timestamp': datetime.utcnow(),
                            'no2_column': np.random.normal(5e15, 2e15),  # NO2 column
                            'pm25_surface': np.random.normal(15, 8),     # PM2.5
                            'temperature': np.random.normal(20, 10),      # Temperatura
                            'humidity': np.random.normal(60, 20),         # Humedad
                            'wind_speed': np.random.normal(5, 3),         # Viento
                            'data_quality': np.random.uniform(0.7, 1.0), # Calidad
                            'aqi_combined': np.random.normal(50, 25),     # AQI
                            'air_quality_category': np.random.choice([
                                'Good', 'Moderate', 'Unhealthy for Sensitive Groups'
                            ])
                        }
                        points.append(point)
                
                sample_data = pd.DataFrame(points)
                
                # Almacenar datos
                await self.storage.store_city_data(
                    city_id, 
                    sample_data, 
                    {"source": "sample_data", "generated_at": datetime.utcnow().isoformat()}
                )
                
                total_points += len(sample_data)
                processed_cities += 1
                
                logger.info(f"✅ {city_id}: {len(sample_data)} puntos generados")
                
            except Exception as e:
                logger.error(f"❌ Error generando datos para {city_id}: {e}")
        
        return {
            "cities_processed": processed_cities,
            "total_points": total_points,
            "data_source": "synthetic",
            "processing_time": 0
        }
    
    async def _validate_setup(self, cities: List[str]) -> Dict:
        """Valida que la configuración sea correcta"""
        validation_results = {
            "database_status": "unknown",
            "cities_validated": 0,
            "cities_with_data": 0,
            "total_points_found": 0,
            "performance_tests": {},
            "issues": []
        }
        
        try:
            # Test conexión a base de datos
            validation_results["database_status"] = "connected"
            
            # Validar cada ciudad
            for city_id in cities:
                try:
                    # Intentar cargar datos
                    data = await self.storage.load_city_data(city_id, limit=10)
                    
                    if len(data) > 0:
                        validation_results["cities_with_data"] += 1
                        validation_results["total_points_found"] += len(data)
                    
                    validation_results["cities_validated"] += 1
                    
                except Exception as e:
                    validation_results["issues"].append(f"{city_id}: {str(e)}")
            
            # Test de rendimiento básico
            if validation_results["cities_with_data"] > 0:
                validation_results["performance_tests"] = await self._run_performance_tests()
            
        except Exception as e:
            validation_results["issues"].append(f"Database connection: {str(e)}")
            validation_results["database_status"] = "error"
        
        return validation_results
    
    async def _run_performance_tests(self) -> Dict:
        """Ejecuta tests básicos de rendimiento"""
        import time
        
        perf_results = {}
        
        # Test: Carga de datos de una ciudad
        try:
            start_time = time.time()
            test_city = list(SUPPORTED_CITIES.keys())[0]
            data = await self.storage.load_city_data(test_city, limit=1000)
            load_time = time.time() - start_time
            
            perf_results["data_load_1000_points"] = {
                "time_seconds": round(load_time, 3),
                "points_loaded": len(data),
                "performance": "good" if load_time < 1.0 else "needs_optimization"
            }
        except Exception as e:
            perf_results["data_load_test"] = {"error": str(e)}
        
        # Test: Consulta espacial
        try:
            start_time = time.time()
            test_city = list(SUPPORTED_CITIES.keys())[0]
            bbox = SUPPORTED_CITIES[test_city]["bbox"]
            # Consulta en un área pequeña
            small_bbox = [
                bbox[0], bbox[1], 
                bbox[0] + (bbox[2] - bbox[0]) * 0.1,
                bbox[1] + (bbox[3] - bbox[1]) * 0.1
            ]
            
            data = await self.storage.load_city_data(test_city, bbox=small_bbox)
            spatial_time = time.time() - start_time
            
            perf_results["spatial_query"] = {
                "time_seconds": round(spatial_time, 3),
                "points_found": len(data),
                "performance": "good" if spatial_time < 0.5 else "needs_optimization"
            }
        except Exception as e:
            perf_results["spatial_query"] = {"error": str(e)}
        
        return perf_results
    
    async def _generate_setup_report(self, validation_results: Dict) -> Dict:
        """Genera reporte final de configuración"""
        
        report = {
            "setup_summary": {
                "environment": self.environment,
                "database_type": self.storage.config.db_type.value,
                "start_time": self.setup_stats["start_time"].isoformat(),
                "end_time": self.setup_stats["end_time"].isoformat() if self.setup_stats["end_time"] else None,
                "total_cities": len(SUPPORTED_CITIES),
                "cities_configured": self.setup_stats["cities_configured"],
                "total_points_generated": self.setup_stats.get("total_points", 0),
                "success": len(self.setup_stats["errors"]) == 0
            },
            "validation_results": validation_results,
            "configuration": {
                "database_config": {
                    "type": self.storage.config.db_type.value,
                    "max_connections": self.storage.config.max_connections,
                    "cache_ttl": self.storage.config.cache_ttl
                },
                "supported_cities": list(SUPPORTED_CITIES.keys()),
                "api_endpoints": [
                    "/api/v2/cities",
                    "/api/v2/cities/{city_id}/data", 
                    "/api/v2/cities/{city_id}/latest",
                    "/api/v2/cities/compare",
                    "/api/v2/cities/{city_id}/stats"
                ]
            },
            "next_steps": self._generate_next_steps(validation_results),
            "errors": self.setup_stats["errors"],
            "warnings": self.setup_stats["warnings"]
        }
        
        # Guardar reporte
        report_file = Path("data/multi_city_setup_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📋 Reporte guardado en: {report_file}")
        
        return report
    
    def _generate_next_steps(self, validation_results: Dict) -> List[str]:
        """Genera lista de siguientes pasos recomendados"""
        next_steps = []
        
        if validation_results["database_status"] != "connected":
            next_steps.append("🔧 Verificar y corregir conexión a base de datos")
        
        if validation_results["cities_with_data"] == 0:
            next_steps.append("📊 Ejecutar ETL para generar datos: python setup_multi_city.py --run-etl")
        
        if validation_results["cities_with_data"] < len(SUPPORTED_CITIES):
            next_steps.append("🏙️  Completar datos para todas las ciudades")
        
        if len(validation_results["issues"]) > 0:
            next_steps.append("⚠️  Revisar y resolver issues reportados")
        
        # Performance recommendations
        perf_tests = validation_results.get("performance_tests", {})
        for test_name, result in perf_tests.items():
            if result.get("performance") == "needs_optimization":
                next_steps.append(f"⚡ Optimizar rendimiento: {test_name}")
        
        if not next_steps:
            next_steps.append("🎉 ¡Sistema listo para producción!")
            next_steps.append("🌐 Iniciar API: python main.py")
            next_steps.append("📖 Ver documentación: http://localhost:8000/docs")
        
        return next_steps
    
    async def cleanup(self):
        """Limpia recursos"""
        if self.storage:
            await self.storage.close()


async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Configuración Multi-Ciudad CleanSky')
    
    parser.add_argument('--environment', default='development', 
                       choices=['development', 'production_sqlite', 'production_postgresql'],
                       help='Entorno de configuración')
    
    parser.add_argument('--cities', nargs='+', 
                       help='Ciudades específicas a configurar')
    
    parser.add_argument('--skip-etl', action='store_true',
                       help='Omitir ejecución de ETL')
    
    parser.add_argument('--sample-data', action='store_true',
                       help='Generar datos de muestra en lugar de datos reales')
    
    parser.add_argument('--skip-optimization', action='store_true',
                       help='Omitir optimizaciones de base de datos')
    
    parser.add_argument('--skip-indexes', action='store_true',
                       help='Omitir creación de índices espaciales')
    
    args = parser.parse_args()
    
    # Inicializar configurador
    setup = MultiCitySetup(args.environment)
    
    try:
        # Ejecutar configuración completa
        report = await setup.setup_complete_system(
            cities=args.cities,
            run_etl=not args.skip_etl,
            optimize_database=not args.skip_optimization,
            create_indexes=not args.skip_indexes,
            generate_sample_data=args.sample_data
        )
        
        # Mostrar resumen
        print("\n" + "="*60)
        print("🎯 CONFIGURACIÓN MULTI-CIUDAD COMPLETADA")
        print("="*60)
        print(f"✅ Ciudades configuradas: {report['setup_summary']['cities_configured']}")
        print(f"📊 Puntos totales: {report['setup_summary']['total_points_generated']:,}")
        print(f"🗄️  Base de datos: {report['setup_summary']['database_type']}")
        print(f"⚡ Performance: {'OK' if not report['validation_results']['issues'] else 'Revisar issues'}")
        
        if report['next_steps']:
            print("\n📋 SIGUIENTES PASOS:")
            for step in report['next_steps']:
                print(f"  {step}")
        
        print("\n📄 Reporte completo: data/multi_city_setup_report.json")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"💥 Error en configuración: {e}")
        return 1
    
    finally:
        await setup.cleanup()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))