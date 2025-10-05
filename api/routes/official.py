"""
Endpoints oficiales CleanSky LA - Fase 3 - Sin emojis
"""
from fastapi import APIRouter, Query, HTTPException
from core.loader import get_dataset, get_dataset_bounds
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Router principal para todos los endpoints oficiales
router = APIRouter()

@router.get("/latest", summary="Ultima malla de risk_score")
async def get_latest(format: str = Query(default="json", regex="^(json|geojson)$")):
    """Devuelve la ultima malla completa con risk_score para cada celda del grid."""
    try:
        ds = get_dataset()
        bounds = get_dataset_bounds()
        
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
                    "name": "CleanSky LA - Latest Risk Grid",
                    "timestamp": "2025-10-05T06:00:00Z",
                    "total_features": len(features),
                    "bounds": bounds
                },
                "features": features
            }
        else:
            return {
                "timestamp": "2025-10-05T06:00:00Z",
                "source": "CleanSky LA - Latest Grid",
                "grid_info": {"total_cells": len(cells), "bounds": bounds},
                "cells": cells,
                "summary": {
                    "high_risk": len([c for c in cells if c["risk_class"] == "high"]),
                    "moderate_risk": len([c for c in cells if c["risk_class"] == "moderate"]),
                    "low_risk": len([c for c in cells if c["risk_class"] == "low"])
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo datos latest: {str(e)}")

@router.get("/forecast", summary="Pronostico de calidad del aire")
async def get_forecast(
    hours: int = Query(default=6, ge=1, le=24),
    model: str = Query(default="mock", regex="^(mock|persistence|advection)$")
):
    """Devuelve pronostico de risk_score para las proximas horas."""
    try:
        ds = get_dataset()
        bounds = get_dataset_bounds()
        current_time = datetime.utcnow()
        
        forecasts = []
        for hour in range(1, hours + 1):
            forecast_time = current_time + timedelta(hours=hour)
            
            # Modelo simple: variacion basica
            if model == "persistence":
                factor = 1.0  # Sin cambios
            elif model == "advection":
                factor = 1.0 + (hour * 0.05)  # Incremento gradual
            else:  # mock
                hour_of_day = (current_time.hour + hour) % 24
                factor = 1.3 if hour_of_day in [9,10,11,17,18,19] else 0.8 if hour_of_day in [2,3,4,5] else 1.0
            
            hour_forecast = {
                "forecast_time": forecast_time.isoformat() + "Z",
                "hour_offset": hour,
                "cells": []
            }
            
            for i, lat in enumerate(ds.lat.values):
                for j, lon in enumerate(ds.lon.values):
                    current_risk = float(ds.risk_score.isel(lat=i, lon=j).values)
                    
                    if not np.isnan(current_risk):
                        predicted_risk = min(100, max(0, current_risk * factor * np.random.uniform(0.9, 1.1)))
                        risk_class = "high" if predicted_risk >= 67 else "moderate" if predicted_risk >= 34 else "low"
                        
                        hour_forecast["cells"].append({
                            "lat": float(lat),
                            "lon": float(lon),
                            "risk_score": predicted_risk,
                            "risk_class": risk_class,
                            "confidence": max(0.5, 1.0 - (hour * 0.08))
                        })
            
            forecasts.append(hour_forecast)
        
        return {
            "timestamp": current_time.isoformat() + "Z",
            "model": model,
            "forecast_hours": hours,
            "bounds": bounds,
            "forecasts": forecasts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando pronostico: {str(e)}")

@router.get("/alerts", summary="Alertas de alta contaminacion")
async def get_alerts(
    threshold: float = Query(default=66.0, ge=0.0, le=100.0),
    format: str = Query(default="json", regex="^(json|geojson)$")
):
    """Devuelve lista de celdas con risk_score > umbral especificado."""
    try:
        ds = get_dataset()
        bounds = get_dataset_bounds()
        current_time = datetime.utcnow()
        
        alert_cells = []
        for i, lat in enumerate(ds.lat.values):
            for j, lon in enumerate(ds.lon.values):
                risk_score = float(ds.risk_score.isel(lat=i, lon=j).values)
                
                if not np.isnan(risk_score) and risk_score > threshold:
                    alert_level = "critical" if risk_score >= 90 else "severe" if risk_score >= 80 else "high"
                    
                    cell = {
                        "lat": float(lat),
                        "lon": float(lon),
                        "risk_score": risk_score,
                        "risk_class": "high" if risk_score >= 67 else "moderate",
                        "alert_level": alert_level,
                        "cell_id": f"{i}_{j}",
                        "exceeded_by": risk_score - threshold,
                        "message": f"ALERTA {alert_level.upper()}: Risk score {risk_score:.1f}"
                    }
                    
                    if "no2" in ds:
                        cell["no2"] = float(ds.no2.isel(lat=i, lon=j).values)
                    if "pm25" in ds:
                        cell["pm25"] = float(ds.pm25.isel(lat=i, lon=j).values)
                    if "o3" in ds:
                        cell["o3"] = float(ds.o3.isel(lat=i, lon=j).values)
                    
                    alert_cells.append(cell)
        
        # Ordenar por risk_score descendente
        alert_cells.sort(key=lambda x: x["risk_score"], reverse=True)
        
        if format == "geojson":
            features = []
            for cell in alert_cells:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [cell["lon"], cell["lat"]]},
                    "properties": {k: v for k, v in cell.items() if k not in ["lat", "lon"]}
                })
            
            return {
                "type": "FeatureCollection",
                "properties": {
                    "name": "CleanSky LA - Active Alerts",
                    "timestamp": current_time.isoformat() + "Z",
                    "alert_threshold": threshold,
                    "total_alerts": len(features),
                    "bounds": bounds
                },
                "features": features
            }
        else:
            return {
                "timestamp": current_time.isoformat() + "Z",
                "alert_threshold": threshold,
                "total_alerts": len(alert_cells),
                "bounds": bounds,
                "status": "active" if len(alert_cells) > 0 else "clear",
                "alerts": alert_cells,
                "summary": {
                    "critical": len([c for c in alert_cells if c["alert_level"] == "critical"]),
                    "severe": len([c for c in alert_cells if c["alert_level"] == "severe"]),
                    "high": len([c for c in alert_cells if c["alert_level"] == "high"]),
                    "max_risk": max([c["risk_score"] for c in alert_cells]) if alert_cells else 0
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo alertas: {str(e)}")

@router.get("/tiles/{z}/{x}/{y}.png", summary="Tiles raster PNG")
async def get_tile(z: int, x: int, y: int):
    """Placeholder para tiles raster - devuelve mensaje por ahora."""
    # Implementacion basica para evitar errores
    return {
        "message": f"Tile {z}/{x}/{y} - Implementacion PNG pendiente",
        "note": "Use /api/heatmap/geojson para datos vectoriales"
    }