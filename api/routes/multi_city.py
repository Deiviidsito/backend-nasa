"""
API Multi-Ciudad - CleanSky North America  
Endpoints que manejan múltiples ciudades
"""
from fastapi import APIRouter, Query, HTTPException, Path
from pathlib import Path as PathLib
import xarray as xr
import numpy as np
from typing import Dict, Any, List, Optional
import sys
import os

# Agregar path para importaciones
sys.path.append(str(PathLib(__file__).parent.parent))

from config_multicity import settings, SUPPORTED_CITIES

router = APIRouter(tags=["Multi-City"])

# Cache global para datasets por ciudad
_city_datasets = {}

def get_city_dataset(city_id: str) -> xr.Dataset:
    """Carga dataset de una ciudad específica (con cache)."""
    global _city_datasets
    
    if city_id not in SUPPORTED_CITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Ciudad no soportada: {city_id}. Disponibles: {list(SUPPORTED_CITIES.keys())}"
        )
    
    if city_id not in _city_datasets:
        try:
            city_data_path = settings.get_city_data_path(city_id)
            dataset_path = city_data_path / "processed" / "airs_risk.nc"
            
            if not dataset_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Dataset no encontrado para {city_id}. Ejecutar ETL primero."
                )
            
            _city_datasets[city_id] = xr.open_dataset(dataset_path)
            print(f"🛰️ Dataset cargado para {SUPPORTED_CITIES[city_id]['name']}")
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error cargando dataset para {city_id}: {str(e)}"
            )
    
    return _city_datasets[city_id]

@router.get("/cities", summary="Lista de ciudades soportadas")
async def list_cities():
    """
    Devuelve lista de todas las ciudades soportadas por CleanSky.
    
    Incluye información básica de cada ciudad como nombre, bounding box, población.
    """
    cities = []
    
    for city_id, config in SUPPORTED_CITIES.items():
        # Verificar si tiene datos disponibles
        city_data_path = settings.get_city_data_path(city_id)
        dataset_path = city_data_path / "processed" / "airs_risk.nc"
        has_data = dataset_path.exists()
        
        cities.append({
            "id": city_id,
            "name": config["name"],
            "bbox": {
                "west": config["bbox"][0],
                "south": config["bbox"][1], 
                "east": config["bbox"][2],
                "north": config["bbox"][3]
            },
            "population": config["population"],
            "timezone": config["timezone"],
            "has_data": has_data,
            "grid_resolution": config["grid_resolution"]
        })
    
    return {
        "total_cities": len(cities),
        "cities": cities,
        "coverage": "North America (TEMPO coverage area)"
    }

@router.get("/cities/{city_id}/latest", summary="Última malla de una ciudad")
async def get_city_latest(
    city_id: str = Path(..., description="ID de la ciudad"),
    format: str = Query(default="json", regex="^(json|geojson)$")
):
    """
    Devuelve la última malla con risk_score para una ciudad específica.
    
    Equivalente a /api/latest pero para cualquier ciudad soportada.
    """
    try:
        ds = get_city_dataset(city_id)
        city_config = SUPPORTED_CITIES[city_id]
        
        cells = []
        for i, lat in enumerate(ds.lat.values):
            for j, lon in enumerate(ds.lon.values):
                risk_score = float(ds.risk_score.isel(lat=i, lon=j).values)
                
                if not np.isnan(risk_score):
                    risk_class = "high" if risk_score >= 67 else "moderate" if risk_score >= 34 else "low"
                    
                    cell = {
                        "lat": float(lat),
                        "lon": float(lon),
                        "risk_score": risk_score,
                        "risk_class": risk_class,
                        "cell_id": f"{i}_{j}"
                    }
                    
                    # Variables adicionales
                    for var in ["no2", "pm25", "o3", "temp", "wind"]:
                        if var in ds:
                            cell[var] = float(ds[var].isel(lat=i, lon=j).values)
                    
                    cells.append(cell)
        
        if format == "geojson":
            features = []
            for cell in cells:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [cell["lon"], cell["lat"]]},
                    "properties": {k: v for k, v in cell.items() if k not in ["lat", "lon"]}
                })
            
            return {
                "type": "FeatureCollection",
                "properties": {
                    "name": f"CleanSky - {city_config['name']}",
                    "city_id": city_id,
                    "timestamp": "2025-10-05T06:00:00Z",
                    "total_features": len(features),
                    "bounds": {
                        "west": city_config["bbox"][0],
                        "south": city_config["bbox"][1],
                        "east": city_config["bbox"][2], 
                        "north": city_config["bbox"][3]
                    }
                },
                "features": features
            }
        else:
            return {
                "city_id": city_id,
                "city_name": city_config["name"],
                "timestamp": "2025-10-05T06:00:00Z",
                "source": f"CleanSky - {city_config['name']}",
                "grid_info": {
                    "total_cells": len(cells),
                    "bounds": {
                        "west": city_config["bbox"][0],
                        "south": city_config["bbox"][1],
                        "east": city_config["bbox"][2],
                        "north": city_config["bbox"][3]
                    }
                },
                "cells": cells,
                "summary": {
                    "high_risk": len([c for c in cells if c["risk_class"] == "high"]),
                    "moderate_risk": len([c for c in cells if c["risk_class"] == "moderate"]),
                    "low_risk": len([c for c in cells if c["risk_class"] == "low"])
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo datos para {city_id}: {str(e)}"
        )

@router.get("/compare", summary="Comparar múltiples ciudades")
async def compare_cities(
    cities: str = Query(..., description="IDs de ciudades separados por coma (ej: los_angeles,new_york)")
):
    """
    Compara estadísticas de calidad del aire entre múltiples ciudades.
    
    Útil para análisis comparativo y rankings.
    """
    try:
        city_ids = [city.strip() for city in cities.split(',')]
        
        # Validar ciudades
        for city_id in city_ids:
            if city_id not in SUPPORTED_CITIES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ciudad no soportada: {city_id}"
                )
        
        comparison = []
        
        for city_id in city_ids:
            try:
                ds = get_city_dataset(city_id)
                city_config = SUPPORTED_CITIES[city_id]
                
                # Calcular estadísticas
                risk_values = ds.risk_score.values.flatten()
                risk_values = risk_values[~np.isnan(risk_values)]
                
                if len(risk_values) > 0:
                    stats = {
                        "city_id": city_id,
                        "city_name": city_config["name"],
                        "population": city_config["population"],
                        "avg_risk_score": float(np.mean(risk_values)),
                        "max_risk_score": float(np.max(risk_values)),
                        "min_risk_score": float(np.min(risk_values)),
                        "std_risk_score": float(np.std(risk_values)),
                        "high_risk_percentage": float(len(risk_values[risk_values >= 67]) / len(risk_values) * 100),
                        "moderate_risk_percentage": float(len(risk_values[(risk_values >= 34) & (risk_values < 67)]) / len(risk_values) * 100),
                        "low_risk_percentage": float(len(risk_values[risk_values < 34]) / len(risk_values) * 100),
                        "total_grid_points": len(risk_values)
                    }
                    
                    # Clasificación general
                    if stats["avg_risk_score"] >= 67:
                        stats["overall_class"] = "high"
                    elif stats["avg_risk_score"] >= 34:
                        stats["overall_class"] = "moderate"
                    else:
                        stats["overall_class"] = "low"
                    
                    comparison.append(stats)
                    
            except Exception as e:
                # Ciudad sin datos - agregar placeholder
                comparison.append({
                    "city_id": city_id,
                    "city_name": SUPPORTED_CITIES[city_id]["name"],
                    "error": f"Sin datos disponibles: {str(e)}"
                })
        
        # Ordenar por avg_risk_score (mejor calidad = menor score)
        valid_cities = [c for c in comparison if "error" not in c]
        valid_cities.sort(key=lambda x: x["avg_risk_score"])
        
        return {
            "timestamp": "2025-10-05T06:00:00Z",
            "comparison_type": "air_quality_ranking",
            "cities_compared": len(city_ids),
            "cities_with_data": len(valid_cities),
            "ranking": valid_cities,
            "errors": [c for c in comparison if "error" in c]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error comparando ciudades: {str(e)}"
        )