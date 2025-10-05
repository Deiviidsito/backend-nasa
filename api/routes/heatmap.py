"""
Devuelve una grilla de riesgo para renderizado en mapas.
"""
from fastapi import APIRouter, Query, HTTPException
from core.loader import get_dataset, get_dataset_bounds, determine_risk_class
from core.models import HeatmapResponse, HeatmapPoint
import numpy as np
from typing import List

router = APIRouter(tags=["Heatmap"])

@router.get(
    "/heatmap",
    response_model=HeatmapResponse,
    summary="Mapa de calor de riesgo",
    description="Retorna una grilla completa de puntos con risk_score para visualización en mapas"
)
async def heatmap(
    resolution: int = Query(
        default=20,
        ge=5,
        le=100,
        description="Resolución de la grilla (puntos por dimensión)"
    ),
    min_risk: float = Query(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Filtro: risk_score mínimo a incluir"
    )
):
    """
    **Genera un mapa de calor de riesgo atmosférico**
    
    Devuelve una grilla de puntos con:
    - 📍 Coordenadas (lat, lon)
    - 🎯 Risk score (0-100)
    - 🏷️ Risk class (low/moderate/high)
    
    Útil para:
    - 🗺️ Visualización en mapas web (Leaflet, Mapbox)
    - 📊 Análisis espacial
    - 🎨 Renderizado de capas de calor
    """
    try:
        ds = get_dataset()
        bounds = get_dataset_bounds()
        
        # Crear grilla subsampling según resolución solicitada
        lat_points = np.linspace(bounds["lat_min"], bounds["lat_max"], resolution)
        lon_points = np.linspace(bounds["lon_min"], bounds["lon_max"], resolution)
        
        points: List[HeatmapPoint] = []
        
        for lat in lat_points:
            for lon in lon_points:
                try:
                    # Usar el punto más cercano
                    data_point = ds.sel(lat=lat, lon=lon, method='nearest')
                    risk_score = float(data_point["risk_score"].values)
                    
                    # Filtrar valores NaN y aplicar filtro mínimo
                    if not np.isnan(risk_score) and risk_score >= min_risk:
                        risk_class = determine_risk_class(risk_score)
                        
                        points.append(HeatmapPoint(
                            lat=float(lat),
                            lon=float(lon),
                            risk_score=risk_score,
                            risk_class=risk_class
                        ))
                        
                except Exception:
                    # Ignorar puntos problemáticos
                    continue
        
        return HeatmapResponse(
            count=len(points),
            bounds=bounds,
            data=points
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando mapa de calor: {str(e)}"
        )

@router.get(
    "/heatmap/geojson",
    summary="Mapa de calor en formato GeoJSON",
    description="Retorna los datos de riesgo en formato GeoJSON para mapas web"
)
async def heatmap_geojson(
    resolution: int = Query(default=15, ge=5, le=50),
    min_risk: float = Query(default=0.0, ge=0.0, le=100.0)
):
    """
    **Mapa de calor en formato GeoJSON**
    
    Formato estándar para librerías de mapas web como:
    - 🍃 Leaflet
    - 🗺️ Mapbox GL JS
    - 🌍 OpenLayers
    """
    try:
        # Reutilizar lógica del endpoint principal
        heatmap_data = await heatmap(resolution=resolution, min_risk=min_risk)
        
        # Convertir a formato GeoJSON
        features = []
        for point in heatmap_data.data:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [point.lon, point.lat]  # GeoJSON usa [lon, lat]
                },
                "properties": {
                    "risk_score": point.risk_score,
                    "risk_class": point.risk_class,
                    "color": get_risk_color(point.risk_class)
                }
            })
        
        return {
            "type": "FeatureCollection",
            "properties": {
                "name": "CleanSky LA Risk Heatmap",
                "count": len(features),
                "bounds": heatmap_data.bounds,
                "generated_at": "2025-10-05T00:00:00Z"
            },
            "features": features
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando GeoJSON: {str(e)}"
        )

def get_risk_color(risk_class: str) -> str:
    """Retorna un color hex basado en la clase de riesgo."""
    color_map = {
        "low": "#00FF00",      # Verde
        "moderate": "#FFFF00", # Amarillo  
        "high": "#FF0000",     # Rojo
        "unknown": "#808080"   # Gris
    }
    return color_map.get(risk_class, "#808080")