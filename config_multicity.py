"""
Configuración Multi-Ciudad para CleanSky North America
Soporte para múltiples ciudades dentro del dominio TEMPO
"""
from pathlib import Path
from typing import Dict, Any
import os

# Directorio base del proyecto
BASE_DIR = Path(__file__).parent

# Configuración de ciudades soportadas (dentro del dominio TEMPO)
SUPPORTED_CITIES = {
    "los_angeles": {
        "name": "Los Angeles, CA",
        "bbox": [-118.7, 33.6, -117.8, 34.4],  # [west, south, east, north]
        "population": 3971883,
        "timezone": "America/Los_Angeles",
        "grid_resolution": 0.03  # grados
    },
    "new_york": {
        "name": "New York, NY", 
        "bbox": [-74.3, 40.4, -73.7, 41.0],
        "population": 8336817,
        "timezone": "America/New_York",
        "grid_resolution": 0.03
    },
    "chicago": {
        "name": "Chicago, IL",
        "bbox": [-88.0, 41.6, -87.5, 42.1],
        "population": 2693976,
        "timezone": "America/Chicago", 
        "grid_resolution": 0.03
    },
    "houston": {
        "name": "Houston, TX",
        "bbox": [-95.8, 29.5, -95.0, 30.1],
        "population": 2320268,
        "timezone": "America/Chicago",
        "grid_resolution": 0.03
    },
    "phoenix": {
        "name": "Phoenix, AZ",
        "bbox": [-112.3, 33.2, -111.7, 33.8],
        "population": 1608139,
        "timezone": "America/Phoenix",
        "grid_resolution": 0.03
    },
    "seattle": {
        "name": "Seattle, WA",
        "bbox": [-122.5, 47.4, -122.1, 47.8],
        "population": 753675,
        "timezone": "America/Los_Angeles",
        "grid_resolution": 0.03
    },
    "miami": {
        "name": "Miami, FL",
        "bbox": [-80.4, 25.6, -80.0, 26.0],
        "population": 442241,
        "timezone": "America/New_York",
        "grid_resolution": 0.03
    },
    "denver": {
        "name": "Denver, CO",
        "bbox": [-105.2, 39.5, -104.7, 40.0],
        "population": 715522,
        "timezone": "America/Denver",
        "grid_resolution": 0.03
    },
    "boston": {
        "name": "Boston, MA",
        "bbox": [-71.3, 42.1, -70.8, 42.6],
        "population": 685094,
        "timezone": "America/New_York",
        "grid_resolution": 0.03
    },
    "atlanta": {
        "name": "Atlanta, GA",
        "bbox": [-84.7, 33.4, -84.1, 33.9],
        "population": 486290,
        "timezone": "America/New_York",
        "grid_resolution": 0.03
    }
}

class MultiCitySettings:
    """Configuración para el sistema multi-ciudad."""
    
    def __init__(self):
        self.base_data_dir = BASE_DIR / "data"
        self.processed_dir = self.base_data_dir / "processed"  
        self.zarr_dir = self.base_data_dir / "zarr_store"
        self.cache_dir = self.base_data_dir / "cache"
        
        # Crear directorios si no existen
        for city_id in SUPPORTED_CITIES.keys():
            city_dir = self.base_data_dir / city_id
            city_dir.mkdir(parents=True, exist_ok=True)
            (city_dir / "processed").mkdir(exist_ok=True)
            (city_dir / "zarr_store").mkdir(exist_ok=True)
    
    def get_city_data_path(self, city_id: str) -> Path:
        """Obtiene el path de datos para una ciudad específica."""
        if city_id not in SUPPORTED_CITIES:
            raise ValueError(f"Ciudad no soportada: {city_id}")
        return self.base_data_dir / city_id
    
    def get_city_bbox(self, city_id: str) -> list:
        """Obtiene el bounding box de una ciudad."""
        if city_id not in SUPPORTED_CITIES:
            raise ValueError(f"Ciudad no soportada: {city_id}")
        return SUPPORTED_CITIES[city_id]["bbox"]
    
    def list_active_cities(self) -> list:
        """Lista ciudades que tienen datasets procesados."""
        active_cities = []
        for city_id in SUPPORTED_CITIES.keys():
            city_path = self.get_city_data_path(city_id)
            dataset_path = city_path / "processed" / "airs_risk.nc"
            if dataset_path.exists():
                active_cities.append(city_id)
        return active_cities

# Instancia global de configuración
settings = MultiCitySettings()