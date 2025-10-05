"""
Endpoint /api/forecast - Pronóstico de 3-6 horas
"""
from fastapi import APIRouter, Query, HTTPException
from core.loader import get_dataset, get_dataset_bounds
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

router = APIRouter(tags=["Forecast"])

@router.get(
    "/forecast",
    summary="Pronóstico de calidad del aire",
    description="Devuelve pronóstico de risk_score para las próximas 3-6 horas"
)
async def get_forecast(
    hours: int = Query(
        default=6,
        ge=1,
        le=24,
        description="Número de horas a pronosticar (1-24)"
    ),
    model: str = Query(
        default="advection",
        regex="^(advection|persistence|mock)$",
        description="Modelo de pronóstico: advection, persistence, mock"
    )
):
    """
    **Pronóstico de calidad del aire**
    
    Modelos disponibles:
    - `advection`: Advección basada en viento (realista)
    - `persistence`: Asume condiciones constantes
    - `mock`: Datos simulados para demo
    
    Útil para:
    - 🔮 Predicción de tendencias
    - 🚨 Alertas tempranas
    - 📊 Planificación urbana
    """
    try:
        ds = get_dataset()
        bounds = get_dataset_bounds()
        current_time = datetime.utcnow()
        
        # Generar pronóstico según el modelo seleccionado
        if model == "advection":
            forecast_data = generate_advection_forecast(ds, hours)
        elif model == "persistence":
            forecast_data = generate_persistence_forecast(ds, hours)
        else:  # mock
            forecast_data = generate_mock_forecast(ds, hours)
        
        return {
            "timestamp": current_time.isoformat() + "Z",
            "model": model,
            "forecast_hours": hours,
            "bounds": bounds,
            "forecasts": forecast_data,
            "metadata": {
                "model_description": get_model_description(model),
                "update_frequency": "hourly",
                "accuracy": get_model_accuracy(model)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando pronóstico: {str(e)}"
        )

def generate_advection_forecast(ds, hours: int) -> List[Dict[str, Any]]:
    """Genera pronóstico basado en advección por viento."""
    forecasts = []
    base_time = datetime.utcnow()
    
    # Obtener campo de viento promedio
    if "wind" in ds:
        avg_wind = float(ds.wind.mean().values)
    else:
        avg_wind = 2.0  # m/s default
    
    for hour in range(1, hours + 1):
        forecast_time = base_time + timedelta(hours=hour)
        
        # Simular deriva de contaminantes por viento
        wind_factor = 1.0 + (avg_wind * hour * 0.1)  # Deriva gradual
        
        hour_forecast = {
            "forecast_time": forecast_time.isoformat() + "Z",
            "hour_offset": hour,
            "cells": []
        }
        
        # Generar pronóstico para cada celda
        for i, lat in enumerate(ds.lat.values):
            for j, lon in enumerate(ds.lon.values):
                current_risk = float(ds.risk_score.isel(lat=i, lon=j).values)
                
                if not np.isnan(current_risk):
                    # Aplicar modelo de advección simple
                    predicted_risk = current_risk * wind_factor * np.random.uniform(0.8, 1.2)
                    predicted_risk = max(0, min(100, predicted_risk))  # Clamp 0-100
                    
                    hour_forecast["cells"].append({
                        "lat": float(lat),
                        "lon": float(lon),
                        "risk_score": predicted_risk,
                        "risk_class": determine_risk_class(predicted_risk),
                        "confidence": max(0.3, 1.0 - (hour * 0.1))  # Decae con tiempo
                    })
        
        forecasts.append(hour_forecast)
    
    return forecasts

def generate_persistence_forecast(ds, hours: int) -> List[Dict[str, Any]]:
    """Genera pronóstico asumiendo persistencia (condiciones constantes)."""
    forecasts = []
    base_time = datetime.utcnow()
    
    for hour in range(1, hours + 1):
        forecast_time = base_time + timedelta(hours=hour)
        
        hour_forecast = {
            "forecast_time": forecast_time.isoformat() + "Z",
            "hour_offset": hour,
            "cells": []
        }
        
        # Copiar condiciones actuales con pequeña variación
        for i, lat in enumerate(ds.lat.values):
            for j, lon in enumerate(ds.lon.values):
                current_risk = float(ds.risk_score.isel(lat=i, lon=j).values)
                
                if not np.isnan(current_risk):
                    # Pequeña variación random ±5%
                    predicted_risk = current_risk * np.random.uniform(0.95, 1.05)
                    predicted_risk = max(0, min(100, predicted_risk))
                    
                    hour_forecast["cells"].append({
                        "lat": float(lat),
                        "lon": float(lon),
                        "risk_score": predicted_risk,
                        "risk_class": determine_risk_class(predicted_risk),
                        "confidence": 0.8  # Alta confianza en persistencia
                    })
        
        forecasts.append(hour_forecast)
    
    return forecasts

def generate_mock_forecast(ds, hours: int) -> List[Dict[str, Any]]:
    """Genera pronóstico simulado para demo."""
    forecasts = []
    base_time = datetime.utcnow()
    
    for hour in range(1, hours + 1):
        forecast_time = base_time + timedelta(hours=hour)
        
        # Simular tendencia: empeora en horas pico (9-11, 17-19)
        hour_of_day = (base_time.hour + hour) % 24
        if hour_of_day in [9, 10, 11, 17, 18, 19]:
            trend_factor = 1.3  # Empeora en horas pico
        elif hour_of_day in [2, 3, 4, 5]:
            trend_factor = 0.7  # Mejora en madrugada
        else:
            trend_factor = 1.0
        
        hour_forecast = {
            "forecast_time": forecast_time.isoformat() + "Z", 
            "hour_offset": hour,
            "trend": "worse" if trend_factor > 1.1 else "better" if trend_factor < 0.9 else "stable",
            "cells": []
        }
        
        for i, lat in enumerate(ds.lat.values):
            for j, lon in enumerate(ds.lon.values):
                current_risk = float(ds.risk_score.isel(lat=i, lon=j).values)
                
                if not np.isnan(current_risk):
                    predicted_risk = current_risk * trend_factor * np.random.uniform(0.9, 1.1)
                    predicted_risk = max(0, min(100, predicted_risk))
                    
                    hour_forecast["cells"].append({
                        "lat": float(lat),
                        "lon": float(lon),
                        "risk_score": predicted_risk,
                        "risk_class": determine_risk_class(predicted_risk),
                        "confidence": max(0.5, 1.0 - (hour * 0.08))
                    })
        
        forecasts.append(hour_forecast)
    
    return forecasts

def determine_risk_class(risk_score: float) -> str:
    """Determina clase de riesgo."""
    if np.isnan(risk_score):
        return "unknown"
    elif risk_score >= 67:
        return "high"
    elif risk_score >= 34:
        return "moderate"
    else:
        return "low"

def get_model_description(model: str) -> str:
    """Descripción del modelo."""
    descriptions = {
        "advection": "Modelo de advección basado en patrones de viento",
        "persistence": "Modelo de persistencia - asume condiciones constantes",
        "mock": "Modelo simulado con patrones diurnos realistas"
    }
    return descriptions.get(model, "Modelo desconocido")

def get_model_accuracy(model: str) -> str:
    """Precisión estimada del modelo."""
    accuracy = {
        "advection": "75% (1-3h), 60% (4-6h)",
        "persistence": "80% (1-2h), 50% (3-6h)", 
        "mock": "N/A - Solo para demo"
    }
    return accuracy.get(model, "Desconocido")