"""
Utilidades comunes para ingesta de datos CleanSky LA.
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Bounding box Los Ángeles (oeste, sur, este, norte)
BBOX_LA = (-118.7, 33.6, -117.8, 34.4)

# Directorios
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "zarr_store"
CACHE_DIR = BASE_DIR / "data" / "cache"

def ensure_data_dirs():
    """Crear directorios necesarios para datos."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
def get_recent_date_range(days_back: int = 1) -> Tuple[str, str]:
    """
    Obtener rango de fechas recientes para descarga.
    
    Args:
        days_back: Días hacia atrás desde hoy
        
    Returns:
        Tuple con (fecha_inicio, fecha_fin) en formato YYYY-MM-DD
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def validate_bbox(bbox: Tuple[float, float, float, float]) -> bool:
    """Validar que el bounding box sea válido."""
    west, south, east, north = bbox
    return (
        -180 <= west <= 180 and
        -180 <= east <= 180 and
        -90 <= south <= 90 and
        -90 <= north <= 90 and
        west < east and
        south < north
    )

def format_bbox_for_openaq(bbox: Tuple[float, float, float, float]) -> str:
    """Formatear bbox para API OpenAQ (west,south,east,north)."""
    return f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"

def get_earthdata_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Obtener credenciales EarthData desde variables de entorno."""
    return os.getenv("EARTHDATA_USERNAME"), os.getenv("EARTHDATA_PASSWORD")

def log_info(message: str):
    """Log simple para debugging."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def log_error(message: str):
    """Log de errores."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ERROR: {message}")

def log_success(message: str):
    """Log de éxito."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ✅ {message}")

# Configuraciones específicas por dataset
TEMPO_CONFIG = {
    "short_name": "TEMPO_NO2_L3_NRT",
    "variable_name": "nitrogendioxide_tropospheric_column",
    "output_name": "no2",
    "zarr_path": "tempo_no2.zarr"
}

IMERG_CONFIG = {
    "short_name": "GPM_3IMERGHH_Late", 
    "variable_name": "precipitationCal",
    "output_name": "rain",
    "zarr_path": "imerg_precip.zarr"
}

MERRA2_CONFIG = {
    "short_name": "M2I1NXASM",
    "variables": ["T2M", "U2M", "V2M"],  # Temperatura, viento U y V
    "zarr_path": "merra2_temp.zarr"
}

OPENAQ_CONFIG = {
    "api_url": "https://api.openaq.org/v3/locations",
    "measurements_url": "https://api.openaq.org/v3/locations/{location_id}/latest",
    "parameters": ["pm25", "no2", "o3"],
    "output_path": "openaq_latest.parquet",
    "headers": {
        "X-API-Key": os.getenv("OPENAQ_API_KEY", "")
    }
}