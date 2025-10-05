"""
Configuración de Base de Datos Optimizada para CleanSky Multi-Ciudad
Manejo eficiente de 3,000+ puntos por ciudad
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
import sqlite3
import asyncpg
import redis
from contextlib import asynccontextmanager
import aiofiles

# Configurar logging
logger = logging.getLogger(__name__)

class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    FILE_SYSTEM = "filesystem"

@dataclass
class DatabaseConfig:
    """Configuración de base de datos"""
    db_type: DatabaseType
    connection_string: str
    max_connections: int = 10
    connection_timeout: int = 30
    query_timeout: int = 60
    cache_ttl: int = 3600
    enable_compression: bool = True
    enable_indexing: bool = True

class OptimizedDataStorage:
    """Almacenamiento optimizado de datos multi-ciudad"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection_pool = None
        self.redis_client = None
        self.data_dir = Path("data/multi_city_optimized")
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # Índices en memoria para búsquedas rápidas
        self._spatial_index = {}
        self._temporal_index = {}
        self._city_metadata = {}
    
    async def initialize(self):
        """Inicializa conexiones y estructuras de datos"""
        logger.info(f"🔧 Inicializando almacenamiento: {self.config.db_type.value}")
        
        if self.config.db_type == DatabaseType.POSTGRESQL:
            await self._init_postgresql()
        elif self.config.db_type == DatabaseType.SQLITE:
            await self._init_sqlite()
        elif self.config.db_type == DatabaseType.REDIS:
            await self._init_redis()
        else:  # FILE_SYSTEM
            await self._init_filesystem()
        
        # Crear índices espaciales
        await self._build_spatial_indexes()
        
        logger.info("✅ Almacenamiento inicializado")
    
    async def _init_postgresql(self):
        """Inicializa pool de conexiones PostgreSQL"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                self.config.connection_string,
                min_size=2,
                max_size=self.config.max_connections,
                command_timeout=self.config.query_timeout
            )
            
            # Crear tablas optimizadas
            async with self.connection_pool.acquire() as conn:
                await self._create_postgresql_tables(conn)
                
            logger.info("✅ PostgreSQL inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando PostgreSQL: {e}")
            raise
    
    async def _create_postgresql_tables(self, conn):
        """Crea tablas PostgreSQL optimizadas"""
        
        # Tabla principal de datos por ciudad
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS city_air_quality (
                id BIGSERIAL PRIMARY KEY,
                city_id VARCHAR(50) NOT NULL,
                longitude DECIMAL(10, 6) NOT NULL,
                latitude DECIMAL(10, 6) NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                
                -- Contaminantes
                no2_column DECIMAL(15, 6),
                o3_column DECIMAL(15, 6),
                pm25_surface DECIMAL(10, 3),
                
                -- Meteorología
                temperature DECIMAL(6, 2),
                humidity DECIMAL(5, 2),
                wind_speed DECIMAL(6, 2),
                wind_direction DECIMAL(6, 2),
                pressure DECIMAL(8, 2),
                
                -- Calidad y métricas
                data_quality DECIMAL(3, 2),
                aqi_pm25 DECIMAL(6, 2),
                aqi_no2 DECIMAL(6, 2),
                aqi_combined DECIMAL(6, 2),
                air_quality_category VARCHAR(50),
                
                -- Metadatos
                data_sources JSONB,
                processing_metadata JSONB,
                
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Índices optimizados para consultas espaciales y temporales
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_city_spatial ON city_air_quality USING GIST (ST_Point(longitude, latitude))",
            "CREATE INDEX IF NOT EXISTS idx_city_id_time ON city_air_quality (city_id, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_city_aqi ON city_air_quality (city_id, aqi_combined DESC)",
            "CREATE INDEX IF NOT EXISTS idx_spatial_quality ON city_air_quality (longitude, latitude, data_quality)",
            "CREATE INDEX IF NOT EXISTS idx_timestamp_quality ON city_air_quality (timestamp, data_quality) WHERE data_quality > 0.5",
            "CREATE INDEX IF NOT EXISTS idx_air_quality_category ON city_air_quality (city_id, air_quality_category, timestamp)",
        ]
        
        for index_sql in indexes:
            try:
                await conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"⚠️  Error creando índice: {e}")
        
        # Tabla de metadatos por ciudad
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS city_metadata (
                city_id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                bbox DECIMAL(10, 6)[4] NOT NULL,
                population BIGINT,
                timezone VARCHAR(50),
                grid_resolution DECIMAL(8, 6),
                
                -- Estadísticas de datos
                total_points BIGINT DEFAULT 0,
                last_update TIMESTAMPTZ,
                data_quality_avg DECIMAL(3, 2),
                coverage_stats JSONB,
                
                -- Configuración
                config JSONB,
                
                created_at TIMESTAMPZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Tabla de estadísticas agregadas por hora
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS city_hourly_stats (
                id BIGSERIAL PRIMARY KEY,
                city_id VARCHAR(50) NOT NULL,
                hour_timestamp TIMESTAMPTZ NOT NULL,
                
                -- Estadísticas agregadas
                avg_aqi DECIMAL(6, 2),
                max_aqi DECIMAL(6, 2),
                avg_no2 DECIMAL(15, 6),
                avg_pm25 DECIMAL(10, 3),
                avg_temperature DECIMAL(6, 2),
                
                -- Conteos
                total_points INTEGER,
                quality_points INTEGER,
                
                -- Distribución por categoría
                category_distribution JSONB,
                
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_hourly_stats 
            ON city_hourly_stats (city_id, hour_timestamp DESC)
        """)
    
    async def _init_sqlite(self):
        """Inicializa base de datos SQLite optimizada"""
        db_path = self.data_dir / "cleansky_optimized.db"
        
        # Crear conexión con optimizaciones
        self.sqlite_conn = sqlite3.connect(
            str(db_path),
            timeout=self.config.connection_timeout,
            check_same_thread=False
        )
        
        # Configuraciones de rendimiento SQLite
        self.sqlite_conn.execute("PRAGMA synchronous = NORMAL")
        self.sqlite_conn.execute("PRAGMA cache_size = 10000")
        self.sqlite_conn.execute("PRAGMA temp_store = MEMORY")
        self.sqlite_conn.execute("PRAGMA mmap_size = 268435456")  # 256MB
        self.sqlite_conn.execute("PRAGMA journal_mode = WAL")
        
        await self._create_sqlite_tables()
        logger.info("✅ SQLite inicializado")
    
    async def _create_sqlite_tables(self):
        """Crea tablas SQLite optimizadas"""
        # Tabla principal simplificada para SQLite
        self.sqlite_conn.execute("""
            CREATE TABLE IF NOT EXISTS city_air_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id TEXT NOT NULL,
                longitude REAL NOT NULL,
                latitude REAL NOT NULL,
                timestamp INTEGER NOT NULL,
                
                no2_column REAL,
                pm25_surface REAL,
                aqi_combined REAL,
                air_quality_category TEXT,
                data_quality REAL,
                
                data_json TEXT,  -- JSON para datos adicionales
                
                created_at INTEGER DEFAULT (strftime('%s','now'))
            )
        """)
        
        # Índices SQLite
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_city_time ON city_air_quality (city_id, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_spatial ON city_air_quality (longitude, latitude)",
            "CREATE INDEX IF NOT EXISTS idx_aqi ON city_air_quality (city_id, aqi_combined DESC)",
        ]
        
        for index_sql in indexes:
            self.sqlite_conn.execute(index_sql)
        
        self.sqlite_conn.commit()
    
    async def _init_redis(self):
        """Inicializa cliente Redis"""
        try:
            self.redis_client = redis.Redis.from_url(
                self.config.connection_string,
                socket_timeout=self.config.connection_timeout,
                decode_responses=True
            )
            
            # Test conexión
            await self.redis_client.ping()
            logger.info("✅ Redis inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando Redis: {e}")
            raise
    
    async def _init_filesystem(self):
        """Inicializa almacenamiento en sistema de archivos optimizado"""
        # Crear estructura de directorios optimizada
        for city_id in ['los_angeles', 'new_york', 'chicago', 'houston', 'phoenix', 
                       'seattle', 'miami', 'denver', 'boston', 'atlanta']:
            city_dir = self.data_dir / city_id
            city_dir.mkdir(exist_ok=True)
            
            # Subdirectorios por tipo de dato
            (city_dir / "latest").mkdir(exist_ok=True)
            (city_dir / "historical").mkdir(exist_ok=True)
            (city_dir / "stats").mkdir(exist_ok=True)
            (city_dir / "cache").mkdir(exist_ok=True)
        
        logger.info("✅ Sistema de archivos inicializado")
    
    async def _build_spatial_indexes(self):
        """Construye índices espaciales en memoria para búsquedas rápidas"""
        logger.info("🔧 Construyendo índices espaciales...")
        
        # Implementar R-tree o quadtree para búsquedas espaciales rápidas
        # Por simplicidad, usar diccionario por ahora
        self._spatial_index = {}
        
        logger.info("✅ Índices espaciales construidos")
    
    async def store_city_data(self, city_id: str, data: pd.DataFrame, 
                            metadata: Optional[Dict] = None) -> bool:
        """
        Almacena datos de ciudad de manera optimizada
        """
        try:
            logger.info(f"💾 Almacenando {len(data)} puntos para {city_id}")
            
            if self.config.db_type == DatabaseType.POSTGRESQL:
                return await self._store_postgresql(city_id, data, metadata)
            elif self.config.db_type == DatabaseType.SQLITE:
                return await self._store_sqlite(city_id, data, metadata)
            elif self.config.db_type == DatabaseType.REDIS:
                return await self._store_redis(city_id, data, metadata)
            else:  # FILE_SYSTEM
                return await self._store_filesystem(city_id, data, metadata)
                
        except Exception as e:
            logger.error(f"❌ Error almacenando datos para {city_id}: {e}")
            return False
    
    async def _store_postgresql(self, city_id: str, data: pd.DataFrame, metadata: Dict) -> bool:
        """Almacena en PostgreSQL con optimizaciones"""
        async with self.connection_pool.acquire() as conn:
            
            # Inserción por lotes optimizada
            insert_sql = """
                INSERT INTO city_air_quality (
                    city_id, longitude, latitude, timestamp,
                    no2_column, o3_column, pm25_surface,
                    temperature, humidity, wind_speed, wind_direction, pressure,
                    data_quality, aqi_pm25, aqi_no2, aqi_combined, air_quality_category,
                    data_sources, processing_metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
            """
            
            # Preparar datos para inserción por lotes
            batch_data = []
            for _, row in data.iterrows():
                batch_data.append((
                    city_id,
                    float(row.get('longitude', 0)),
                    float(row.get('latitude', 0)),
                    row.get('timestamp', datetime.utcnow()),
                    row.get('no2_column'),
                    row.get('o3_column'),
                    row.get('pm25_surface'),
                    row.get('temperature'),
                    row.get('humidity'),
                    row.get('wind_speed'),
                    row.get('wind_direction'),
                    row.get('pressure'),
                    row.get('data_quality', 0.0),
                    row.get('aqi_pm25'),
                    row.get('aqi_no2'),
                    row.get('aqi_combined'),
                    row.get('air_quality_category'),
                    json.dumps({'sources': ['tempo', 'openaq', 'merra2']}),
                    json.dumps(metadata or {})
                ))
            
            # Inserción por lotes
            await conn.executemany(insert_sql, batch_data)
            
            # Actualizar metadatos de ciudad
            await self._update_city_metadata_postgresql(conn, city_id, len(data), metadata)
            
            return True
    
    async def _store_filesystem(self, city_id: str, data: pd.DataFrame, metadata: Dict) -> bool:
        """Almacena en sistema de archivos optimizado"""
        city_dir = self.data_dir / city_id
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # 1. Archivo principal comprimido
        latest_file = city_dir / "latest" / f"{city_id}_latest.parquet"
        data.to_parquet(latest_file, compression='gzip', index=False)
        
        # 2. Archivo histórico
        historical_file = city_dir / "historical" / f"{city_id}_{timestamp}.parquet"
        data.to_parquet(historical_file, compression='gzip', index=False)
        
        # 3. CSV para compatibilidad
        csv_file = city_dir / "latest" / f"{city_id}_latest.csv"
        data.to_csv(csv_file, index=False)
        
        # 4. Índice espacial simplificado
        spatial_index = {
            'bounds': {
                'min_lon': float(data['longitude'].min()),
                'max_lon': float(data['longitude'].max()),
                'min_lat': float(data['latitude'].min()),
                'max_lat': float(data['latitude'].max())
            },
            'total_points': len(data),
            'grid_size': {'lon': len(data['longitude'].unique()), 'lat': len(data['latitude'].unique())}
        }
        
        index_file = city_dir / "cache" / f"{city_id}_spatial_index.json"
        async with aiofiles.open(index_file, 'w') as f:
            await f.write(json.dumps(spatial_index, indent=2))
        
        # 5. Estadísticas precalculadas
        stats = await self._calculate_city_stats(data)
        stats_file = city_dir / "stats" / f"{city_id}_stats.json"
        async with aiofiles.open(stats_file, 'w') as f:
            await f.write(json.dumps(stats, indent=2))
        
        # 6. Metadatos
        metadata_extended = {
            **metadata,
            'last_update': datetime.utcnow().isoformat(),
            'total_points': len(data),
            'file_paths': {
                'latest_parquet': str(latest_file),
                'latest_csv': str(csv_file),
                'historical': str(historical_file),
                'stats': str(stats_file)
            }
        }
        
        metadata_file = city_dir / f"{city_id}_metadata.json"
        async with aiofiles.open(metadata_file, 'w') as f:
            await f.write(json.dumps(metadata_extended, indent=2))
        
        logger.info(f"✅ Datos almacenados para {city_id}: {len(data)} puntos")
        return True
    
    async def load_city_data(self, city_id: str, 
                           bbox: Optional[List[float]] = None,
                           limit: Optional[int] = None,
                           min_quality: Optional[float] = None) -> pd.DataFrame:
        """
        Carga datos de ciudad con filtros optimizados
        """
        try:
            if self.config.db_type == DatabaseType.POSTGRESQL:
                return await self._load_postgresql(city_id, bbox, limit, min_quality)
            elif self.config.db_type == DatabaseType.SQLITE:
                return await self._load_sqlite(city_id, bbox, limit, min_quality)
            elif self.config.db_type == DatabaseType.REDIS:
                return await self._load_redis(city_id, bbox, limit, min_quality)
            else:  # FILE_SYSTEM
                return await self._load_filesystem(city_id, bbox, limit, min_quality)
                
        except Exception as e:
            logger.error(f"❌ Error cargando datos para {city_id}: {e}")
            raise
    
    async def _load_filesystem(self, city_id: str, bbox: Optional[List[float]], 
                             limit: Optional[int], min_quality: Optional[float]) -> pd.DataFrame:
        """Carga optimizada desde sistema de archivos"""
        city_dir = self.data_dir / city_id
        
        # Intentar cargar desde Parquet primero (más rápido)
        parquet_file = city_dir / "latest" / f"{city_id}_latest.parquet"
        
        if parquet_file.exists():
            data = pd.read_parquet(parquet_file)
        else:
            # Fallback a CSV
            csv_file = city_dir / "latest" / f"{city_id}_latest.csv"
            if not csv_file.exists():
                raise FileNotFoundError(f"No se encontraron datos para {city_id}")
            data = pd.read_csv(csv_file)
        
        # Aplicar filtros
        if bbox:
            west, south, east, north = bbox
            data = data[
                (data['longitude'] >= west) &
                (data['longitude'] <= east) &
                (data['latitude'] >= south) &
                (data['latitude'] <= north)
            ]
        
        if min_quality and 'data_quality' in data.columns:
            data = data[data['data_quality'] >= min_quality]
        
        if limit:
            data = data.head(limit)
        
        logger.info(f"📊 Cargados {len(data)} puntos para {city_id}")
        return data
    
    async def _calculate_city_stats(self, data: pd.DataFrame) -> Dict:
        """Calcula estadísticas precalculadas para una ciudad"""
        stats = {
            'total_points': len(data),
            'spatial_coverage': {
                'min_longitude': float(data['longitude'].min()),
                'max_longitude': float(data['longitude'].max()),
                'min_latitude': float(data['latitude'].min()),
                'max_latitude': float(data['latitude'].max())
            },
            'data_quality': {
                'mean_quality': float(data['data_quality'].mean()) if 'data_quality' in data.columns else None,
                'points_high_quality': int((data['data_quality'] > 0.8).sum()) if 'data_quality' in data.columns else None
            }
        }
        
        # Estadísticas de contaminantes
        if 'aqi_combined' in data.columns:
            aqi_data = data['aqi_combined'].dropna()
            if len(aqi_data) > 0:
                stats['air_quality'] = {
                    'mean_aqi': float(aqi_data.mean()),
                    'max_aqi': float(aqi_data.max()),
                    'min_aqi': float(aqi_data.min()),
                    'percentiles': {
                        'p50': float(aqi_data.quantile(0.5)),
                        'p75': float(aqi_data.quantile(0.75)),
                        'p90': float(aqi_data.quantile(0.9))
                    }
                }
        
        # Distribución por categorías
        if 'air_quality_category' in data.columns:
            category_dist = data['air_quality_category'].value_counts()
            stats['category_distribution'] = category_dist.to_dict()
        
        stats['generated_at'] = datetime.utcnow().isoformat()
        
        return stats
    
    async def get_city_stats(self, city_id: str) -> Dict:
        """Obtiene estadísticas precalculadas de una ciudad"""
        if self.config.db_type == DatabaseType.FILE_SYSTEM:
            stats_file = self.data_dir / city_id / "stats" / f"{city_id}_stats.json"
            
            if stats_file.exists():
                async with aiofiles.open(stats_file, 'r') as f:
                    content = await f.read()
                    return json.loads(content)
        
        # Si no hay estadísticas precalculadas, calcular on-the-fly
        data = await self.load_city_data(city_id)
        return await self._calculate_city_stats(data)
    
    async def cleanup_old_data(self, days_to_keep: int = 7):
        """Limpia datos antiguos para optimizar espacio"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        if self.config.db_type == DatabaseType.POSTGRESQL:
            async with self.connection_pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM city_air_quality WHERE timestamp < $1",
                    cutoff_date
                )
        
        elif self.config.db_type == DatabaseType.FILE_SYSTEM:
            # Limpiar archivos históricos antiguos
            for city_dir in self.data_dir.iterdir():
                if city_dir.is_dir():
                    historical_dir = city_dir / "historical"
                    if historical_dir.exists():
                        for file in historical_dir.glob("*.parquet"):
                            if file.stat().st_mtime < cutoff_date.timestamp():
                                file.unlink()
        
        logger.info(f"🧹 Limpieza completada: eliminados datos anteriores a {cutoff_date}")
    
    async def close(self):
        """Cierra conexiones y limpia recursos"""
        if self.connection_pool:
            await self.connection_pool.close()
        
        if self.sqlite_conn:
            self.sqlite_conn.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("🔒 Conexiones de base de datos cerradas")

# Configuraciones predefinidas
DATABASE_CONFIGS = {
    "development": DatabaseConfig(
        db_type=DatabaseType.FILE_SYSTEM,
        connection_string="",
        max_connections=5,
        cache_ttl=1800  # 30 minutos
    ),
    
    "production_sqlite": DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        connection_string="sqlite:///data/cleansky_production.db",
        max_connections=10,
        cache_ttl=3600  # 1 hora
    ),
    
    "production_postgresql": DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        connection_string=os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/cleansky"),
        max_connections=20,
        cache_ttl=3600,
        enable_compression=True,
        enable_indexing=True
    ),
    
    "production_redis": DatabaseConfig(
        db_type=DatabaseType.REDIS,
        connection_string=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        max_connections=15,
        cache_ttl=1800
    )
}

def get_database_config(environment: str = "development") -> DatabaseConfig:
    """Obtiene configuración de base de datos según el entorno"""
    return DATABASE_CONFIGS.get(environment, DATABASE_CONFIGS["development"])

# Instancia global (singleton)
_storage_instance = None

async def get_storage(environment: str = "development") -> OptimizedDataStorage:
    """Obtiene instancia singleton de almacenamiento optimizado"""
    global _storage_instance
    
    if _storage_instance is None:
        config = get_database_config(environment)
        _storage_instance = OptimizedDataStorage(config)
        await _storage_instance.initialize()
    
    return _storage_instance