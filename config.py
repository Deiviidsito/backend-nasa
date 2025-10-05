"""Configuración central del sistema CleanSky LA."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Settings:
    """Configuración de la aplicación."""
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    RAILWAY_ENVIRONMENT: str = os.getenv("RAILWAY_ENVIRONMENT", "development")
    
    # NASA EarthData Credentials
    EARTHDATA_USERNAME: str = os.getenv("EARTHDATA_USERNAME", "")
    EARTHDATA_PASSWORD: str = os.getenv("EARTHDATA_PASSWORD", "")
    
    # CORS Configuration
    CORS_ORIGINS: list = [
        origin.strip() 
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    ]
    
    # OpenAQ API Configuration
    OPENAQ_API_URL: str = os.getenv("OPENAQ_API_URL", "https://api.openaq.org/v3")
    OPENAQ_API_KEY: str = os.getenv("OPENAQ_API_KEY", "")
    
    # Data Storage
    DATA_PATH: Path = Path(os.getenv("DATA_PATH", "./data"))
    ZARR_STORE_PATH: Path = Path(os.getenv("ZARR_STORE_PATH", "./data/zarr_store"))
    
    # OpenAQ API
    OPENAQ_API_URL: str = os.getenv("OPENAQ_API_URL", "https://api.openaq.org/v3")
    
    # Los Angeles Bounding Box
    BBOX_LA = (
        float(os.getenv("BBOX_LA_WEST", "-118.7")),
        float(os.getenv("BBOX_LA_SOUTH", "33.6")),
        float(os.getenv("BBOX_LA_EAST", "-117.8")),
        float(os.getenv("BBOX_LA_NORTH", "34.4")),
    )
    
    # Grid Resolution
    GRID_RESOLUTION: float = float(os.getenv("GRID_RESOLUTION", "0.05"))
    
    # Update Interval
    UPDATE_INTERVAL: int = int(os.getenv("UPDATE_INTERVAL", "60"))
    
    # Alert Thresholds
    ALERT_THRESHOLD_HIGH: int = int(os.getenv("ALERT_THRESHOLD_HIGH", "67"))
    ALERT_THRESHOLD_MODERATE: int = int(os.getenv("ALERT_THRESHOLD_MODERATE", "34"))
    
    def __init__(self):
        """Crear directorios necesarios."""
        self.DATA_PATH.mkdir(parents=True, exist_ok=True)
        self.ZARR_STORE_PATH.mkdir(parents=True, exist_ok=True)
    
    def validate_earthdata_credentials(self) -> bool:
        """Validar que las credenciales de EarthData estén configuradas."""
        return bool(self.EARTHDATA_USERNAME and self.EARTHDATA_PASSWORD)
    
    def get_bbox_dict(self) -> dict:
        """Retornar bounding box como diccionario."""
        return {
            "west": self.BBOX_LA[0],
            "south": self.BBOX_LA[1],
            "east": self.BBOX_LA[2],
            "north": self.BBOX_LA[3],
        }

# Instancia global de configuración
settings = Settings()
