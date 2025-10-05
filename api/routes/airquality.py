"""
Endpoint principal: /api/airquality
Consulta de riesgo atmosférico por coordenadas
"""
from fastapi import APIRouter, Query, HTTPException
from core.loader import get_risk_at_point, get_dataset_bounds
from core.models import AirQualityResponse, ErrorResponse

router = APIRouter(tags=["Air Quality"])

@router.get(
    "/airquality", 
    response_model=AirQualityResponse,
    summary="Consultar calidad del aire",
    description="Devuelve el índice de riesgo atmosférico (AIR Risk Score) y variables base interpoladas desde el dataset para coordenadas específicas en Los Ángeles."
)
async def airquality(
    lat: float = Query(
        ..., 
        ge=33.0, 
        le=35.0, 
        description="Latitud en Los Ángeles (33.0 - 35.0)",
        example=34.05
    ),
    lon: float = Query(
        ..., 
        ge=-119.0, 
        le=-117.0, 
        description="Longitud en Los Ángeles (-119.0 - -117.0)",  
        example=-118.25
    )
):
    """
    **Consulta el riesgo atmosférico para un punto específico**
    
    Este endpoint interpola los datos del dataset satelital para devolver:
    - **risk_score**: Índice de riesgo de 0-100
    - **risk_class**: Clasificación (low/moderate/high)
    - **Variables ambientales**: NO₂, O₃, PM2.5, temperatura, viento
    
    Los datos provienen de la fusión de:
    - 🛰️ NASA TEMPO (NO₂, O₃)
    - 🌫️ OpenAQ (PM2.5)
    - 🌡️ NASA MERRA-2 (meteorología)
    """
    try:
        # Validar que las coordenadas estén dentro del dataset
        bounds = get_dataset_bounds()
        
        if not (bounds["lat_min"] <= lat <= bounds["lat_max"]):
            raise HTTPException(
                status_code=422,
                detail=f"Latitud {lat} fuera del rango del dataset [{bounds['lat_min']:.2f}, {bounds['lat_max']:.2f}]"
            )
        
        if not (bounds["lon_min"] <= lon <= bounds["lon_max"]):
            raise HTTPException(
                status_code=422,
                detail=f"Longitud {lon} fuera del rango del dataset [{bounds['lon_min']:.2f}, {bounds['lon_max']:.2f}]"
            )
        
        # Obtener datos interpolados
        result = get_risk_at_point(lat, lon)
        return AirQualityResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get(
    "/bounds",
    summary="Límites del dataset", 
    description="Retorna los límites geográficos del dataset de riesgo atmosférico"
)
async def get_bounds():
    """Obtiene los límites geográficos del dataset."""
    try:
        bounds = get_dataset_bounds()
        return {
            "bounds": bounds,
            "description": "Límites geográficos del dataset AIR Risk Score",
            "coverage": "Los Ángeles, California"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo límites del dataset: {str(e)}"
        )