"""
Modelos de datos (Pydantic) para respuestas JSON
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class AirQualityResponse(BaseModel):
    """Respuesta del endpoint de calidad del aire."""
    latitude: float = Field(..., description="Latitud del punto consultado")
    longitude: float = Field(..., description="Longitud del punto consultado")
    risk_score: float = Field(..., description="Índice de riesgo atmosférico (0-100)")
    risk_class: str = Field(..., description="Clasificación de riesgo: low, moderate, high, unknown")
    no2: Optional[float] = Field(None, description="Concentración NO₂ (molec/cm²)")
    o3: Optional[float] = Field(None, description="Concentración O₃ (ppm)")
    pm25: Optional[float] = Field(None, description="Concentración PM2.5 (µg/m³)")
    temp: Optional[float] = Field(None, description="Temperatura (K)")
    wind: Optional[float] = Field(None, description="Velocidad del viento (m/s)")

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 34.05,
                "longitude": -118.25,
                "risk_score": 27.3,
                "risk_class": "moderate",
                "no2": 1.3e+15,
                "o3": 0.00028,
                "pm25": 14.6,
                "temp": 296.4,
                "wind": 3.7
            }
        }

class HealthResponse(BaseModel):
    """Respuesta del endpoint de salud."""
    status: str
    timestamp: str
    service: str
    version: str
    dataset_info: Optional[Dict[str, Any]] = None

class HeatmapPoint(BaseModel):
    """Punto individual del mapa de calor."""
    lat: float
    lon: float
    risk_score: float
    risk_class: str

class HeatmapResponse(BaseModel):
    """Respuesta del endpoint de mapa de calor."""
    count: int = Field(..., description="Número total de puntos")
    bounds: Dict[str, float] = Field(..., description="Límites geográficos del dataset")
    data: List[HeatmapPoint] = Field(..., description="Array de puntos con riesgo")

class ErrorResponse(BaseModel):
    """Respuesta estándar para errores."""
    error: str
    detail: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())