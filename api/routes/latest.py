"""
Endpoint /api/latest - Devuelve última malla con risk_score
"""
from fastapi import APIRouter, Query, HTTPException
from core.loader import get_dataset, get_dataset_bounds
import numpy as np
from typing import List, Dict, Anyoint /api/latest - Devuelve última malla con risk_score
"""
from fastapi import APIRouter, Query
from core.loader import get_dataset, get_dataset_bounds
from core.models import HeatmapPoint
import numpy as np
from typing import List, Dict, Any

router = APIRouter(tags=["Latest Data"])

@router.get(
    "/latest",
    summary="Última malla de risk_score",
    description="Devuelve la última malla completa con risk_score para cada celda del grid"
)
async def get_latest(
    format: str = Query(
        default="json",
        regex="^(json|geojson)$",
        description="Formato de respuesta: json o geojson"
    )
):
    """
    **Devuelve la última malla con risk_score**
    
    Formato de respuesta configurable:
    - `json`: Lista simple de celdas
    - `geojson`: FeatureCollection para mapas web
    
    Útil para:
    - Cargar estado actual en el mapa
    - Dashboard de monitoreo
    - Sincronización inicial del frontend
    """
    try:
        ds = get_dataset()
        bounds = get_dataset_bounds()
        
        # Obtener todas las celdas del grid
        cells = []
        
        for i, lat in enumerate(ds.lat.values):
            for j, lon in enumerate(ds.lon.values):
                # Extraer valores para esta celda
                risk_score = float(ds.risk_score.isel(lat=i, lon=j).values)
                
                # Solo incluir celdas válidas (no NaN)
                if not np.isnan(risk_score):
                    risk_class = determine_risk_class(risk_score)
                    
                    cell = {
                        "lat": float(lat),
                        "lon": float(lon),
                        "risk_score": risk_score,
                        "risk_class": risk_class,
                        "cell_id": f"{i}_{j}"
                    }
                    
                    # Agregar variables adicionales si están disponibles
                    if "no2" in ds:
                        cell["no2"] = float(ds.no2.isel(lat=i, lon=j).values)
                    if "pm25" in ds:
                        cell["pm25"] = float(ds.pm25.isel(lat=i, lon=j).values)
                    if "o3" in ds:
                        cell["o3"] = float(ds.o3.isel(lat=i, lon=j).values)
                    if "temp" in ds:
                        cell["temp"] = float(ds.temp.isel(lat=i, lon=j).values)
                    if "wind" in ds:
                        cell["wind"] = float(ds.wind.isel(lat=i, lon=j).values)
                    
                    cells.append(cell)
        
        # Respuesta según formato solicitado
        if format == "geojson":
            return create_geojson_response(cells, bounds)
        else:
            return create_json_response(cells, bounds)
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo datos latest: {str(e)}"
        )

def determine_risk_class(risk_score: float) -> str:
    """Determina la clase de riesgo basada en el score."""
    if np.isnan(risk_score):
        return "unknown"
    elif risk_score >= 67:
        return "high"
    elif risk_score >= 34:
        return "moderate"
    else:
        return "low"

def create_json_response(cells: List[Dict], bounds: Dict) -> Dict[str, Any]:
    """Crea respuesta en formato JSON simple."""
    return {
        "timestamp": "2025-10-05T06:00:00Z",
        "source": "CleanSky LA - Latest Grid",
        "grid_info": {
            "total_cells": len(cells),
            "bounds": bounds,
            "resolution": "15x20 grid"
        },
        "cells": cells,
        "summary": {
            "high_risk": len([c for c in cells if c["risk_class"] == "high"]),
            "moderate_risk": len([c for c in cells if c["risk_class"] == "moderate"]),
            "low_risk": len([c for c in cells if c["risk_class"] == "low"])
        }
    }

def create_geojson_response(cells: List[Dict], bounds: Dict) -> Dict[str, Any]:
    """Crea respuesta en formato GeoJSON."""
    features = []
    
    for cell in cells:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [cell["lon"], cell["lat"]]
            },
            "properties": {
                "risk_score": cell["risk_score"],
                "risk_class": cell["risk_class"],
                "cell_id": cell["cell_id"],
                "color": get_risk_color(cell["risk_class"]),
                **{k: v for k, v in cell.items() if k not in ["lat", "lon", "cell_id"]}
            }
        })
    
    return {
        "type": "FeatureCollection",
        "properties": {
            "name": "CleanSky LA - Latest Risk Grid",
            "timestamp": "2025-10-05T06:00:00Z",
            "total_features": len(features),
            "bounds": bounds
        },
        "features": features
    }

def get_risk_color(risk_class: str) -> str:
    """Retorna color para la clase de riesgo."""
    color_map = {
        "low": "#00FF00",      # Verde
        "moderate": "#FFFF00", # Amarillo  
        "high": "#FF0000",     # Rojo
        "unknown": "#808080"   # Gris
    }
    return color_map.get(risk_class, "#808080")