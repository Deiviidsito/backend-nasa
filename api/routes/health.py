"""
Endpoint de salud del sistema
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from core.loader import get_dataset_info
from core.models import HealthResponse

router = APIRouter(tags=["Health"])

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Estado del sistema",
    description="Verifica el estado de la API y la disponibilidad del dataset"
)
async def health_check():
    """
    **Health check endpoint**
    
    Verifica:
    - ✅ Estado general de la API
    - 🛰️ Disponibilidad del dataset NetCDF
    - 📊 Información básica del dataset
    """
    try:
        # Intentar obtener información del dataset
        dataset_info = get_dataset_info()
        
        return HealthResponse(
            status="ok",
            timestamp=datetime.utcnow().isoformat() + "Z",
            service="CleanSky Los Ángeles API",
            version="1.0.0",
            dataset_info=dataset_info
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Servicio no disponible: Error cargando dataset - {str(e)}"
        )

@router.get(
    "/status",
    summary="Estado detallado",
    description="Información detallada del sistema y dataset"
)
async def detailed_status():
    """Estado detallado del sistema con métricas del dataset."""
    try:
        dataset_info = get_dataset_info()
        
        return {
            "api": {
                "status": "operational",
                "version": "1.0.0",
                "uptime": datetime.utcnow().isoformat() + "Z"
            },
            "dataset": {
                "status": "loaded",
                "path": "data/processed/airs_risk.nc",
                "info": dataset_info
            },
            "endpoints": {
                "airquality": "/api/airquality",
                "heatmap": "/api/heatmap", 
                "bounds": "/api/bounds",
                "docs": "/docs"
            },
            "data_sources": {
                "tempo": "NASA TEMPO (NO₂, O₃)",
                "openaq": "OpenAQ (PM2.5)",
                "merra2": "NASA MERRA-2 (Meteorología)"
            }
        }
        
    except Exception as e:
        return {
            "api": {
                "status": "degraded",
                "version": "1.0.0",
                "error": str(e)
            },
            "dataset": {
                "status": "error",
                "error": str(e)
            }
        }