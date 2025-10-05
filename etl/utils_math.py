"""
Funciones auxiliares matemáticas para normalización y cálculo del índice de riesgo.
CleanSky Los Ángeles - Fase 2: Procesamiento AIR Risk Score
"""

import numpy as np
import xarray as xr
from typing import Optional

def minmax_normalize(da: xr.DataArray) -> xr.DataArray:
    """
    Normaliza una variable entre 0 y 1 evitando NaN.
    
    Args:
        da: DataArray a normalizar
        
    Returns:
        DataArray normalizado entre 0-1
    """
    min_val = da.min()
    max_val = da.max()
    range_val = max_val - min_val
    
    # Evitar división por cero
    if range_val == 0 or np.isnan(range_val):
        return xr.zeros_like(da)
    
    return (da - min_val) / (range_val + 1e-9)

def compute_wind_speed(u: xr.DataArray, v: xr.DataArray) -> xr.DataArray:
    """
    Calcula la velocidad del viento (magnitud del vector).
    
    Args:
        u: Componente U del viento (m/s)
        v: Componente V del viento (m/s)
        
    Returns:
        Velocidad del viento (m/s)
    """
    return np.sqrt(u**2 + v**2)

def classify_risk(score: xr.DataArray) -> xr.DataArray:
    """
    Clasifica el riesgo en 3 categorías basado en el score.
    
    Args:
        score: Array de scores de riesgo (0-100)
        
    Returns:
        Array de categorías: 'good', 'moderate', 'bad'
    """
    # Crear array de strings con la misma forma
    result = xr.full_like(score, "good", dtype="<U8")
    
    # Aplicar condiciones
    result = xr.where(score >= 34, "moderate", result)
    result = xr.where(score > 66, "bad", result)
    
    return result

def compute_aqi_component(value: xr.DataArray, thresholds: list, aqi_breaks: list) -> xr.DataArray:
    """
    Calcula componente AQI para un contaminante específico.
    
    Args:
        value: Concentración del contaminante
        thresholds: Lista de umbrales de concentración
        aqi_breaks: Lista de valores AQI correspondientes
        
    Returns:
        Componente AQI (0-500)
    """
    aqi = xr.zeros_like(value)
    
    for i in range(len(thresholds) - 1):
        mask = (value >= thresholds[i]) & (value < thresholds[i + 1])
        if mask.any():
            # Interpolación linear dentro del rango
            aqi_range = aqi_breaks[i + 1] - aqi_breaks[i]
            conc_range = thresholds[i + 1] - thresholds[i]
            aqi = xr.where(mask, 
                          aqi_breaks[i] + (value - thresholds[i]) * aqi_range / conc_range,
                          aqi)
    
    # Valores por encima del último umbral
    mask = value >= thresholds[-1]
    aqi = xr.where(mask, aqi_breaks[-1], aqi)
    
    return aqi

def compute_risk_enhanced(no2: Optional[xr.DataArray] = None,
                         o3: Optional[xr.DataArray] = None, 
                         pm25: Optional[xr.DataArray] = None,
                         temp: Optional[xr.DataArray] = None,
                         wind: Optional[xr.DataArray] = None,
                         aerosol: Optional[xr.DataArray] = None,
                         rain: Optional[xr.DataArray] = None) -> xr.DataArray:
    """
    Calcula el índice de riesgo atmosférico ponderado (0–100).
    Los pesos están basados en impacto ambiental y dispersión.
    
    Args:
        no2: Concentración NO₂ (molec/cm² o ppb)
        o3: Concentración O₃ (ppb)
        pm25: Concentración PM2.5 (µg/m³)
        temp: Temperatura (K)
        wind: Velocidad del viento (m/s)
        aerosol: Aerosoles (opcional)
        rain: Precipitación (opcional, mm/hr)
        
    Returns:
        Risk score (0-100)
    """
    risk = xr.zeros_like(list(filter(None, [no2, o3, pm25, temp, wind]))[0])
    total_weight = 0
    
    # NO₂ (30% peso) - Contaminante primario
    if no2 is not None:
        no2_norm = minmax_normalize(no2)
        risk += 0.30 * no2_norm
        total_weight += 0.30
    
    # O₃ (25% peso) - Ozono troposférico
    if o3 is not None:
        o3_norm = minmax_normalize(o3)
        risk += 0.25 * o3_norm
        total_weight += 0.25
    
    # PM2.5 (20% peso) - Material particulado
    if pm25 is not None:
        pm25_norm = minmax_normalize(pm25)
        risk += 0.20 * pm25_norm
        total_weight += 0.20
    
    # Temperatura (10% peso) - Factor de dispersión
    if temp is not None:
        # Temperaturas altas favorecen reacciones fotoquímicas
        temp_celsius = temp - 273.15 if temp.mean() > 200 else temp
        temp_risk = xr.where(temp_celsius > 25, (temp_celsius - 25) / 15, 0)
        temp_risk = xr.where(temp_risk > 1, 1, temp_risk)  # Limitar a 1
        risk += 0.10 * temp_risk
        total_weight += 0.10
    
    # Viento (10% peso) - Factor de dispersión (inverso)
    if wind is not None:
        # Viento bajo penaliza (menos dispersión)
        wind_risk = xr.where(wind < 2.0, 1.0, xr.where(wind < 5.0, (5.0 - wind) / 3.0, 0.0))
        risk += 0.10 * wind_risk
        total_weight += 0.10
    
    # Aerosoles (5% peso) - Opcional
    if aerosol is not None:
        aerosol_norm = minmax_normalize(aerosol)
        risk += 0.05 * aerosol_norm
        total_weight += 0.05
    
    # Precipitación (factor reductor) - Opcional
    if rain is not None:
        # La lluvia reduce el riesgo (washout)
        rain_factor = xr.where(rain > 1.0, 0.9, xr.where(rain > 0.1, 0.95, 1.0))
        risk *= rain_factor
    
    # Normalizar por peso total y escalar a 0-100
    if total_weight > 0:
        risk = (risk / total_weight) * 100
    
    # Asegurar rango 0-100
    risk = xr.where(risk < 0, 0, risk)
    risk = xr.where(risk > 100, 100, risk)
    
    return risk

def compute_risk_simple(no2: Optional[xr.DataArray] = None,
                       o3: Optional[xr.DataArray] = None,
                       pm25: Optional[xr.DataArray] = None,
                       temp: Optional[xr.DataArray] = None,
                       wind: Optional[xr.DataArray] = None,
                       aerosol: Optional[xr.DataArray] = None,
                       rain: Optional[xr.DataArray] = None) -> xr.DataArray:
    """
    Versión simplificada del cálculo de riesgo para compatibilidad.
    """
    return compute_risk_enhanced(no2, o3, pm25, temp, wind, aerosol, rain)

# Alias para compatibilidad
compute_risk = compute_risk_simple

def validate_risk_dataset(ds: xr.Dataset) -> dict:
    """
    Valida que el dataset de riesgo tenga la estructura esperada.
    
    Args:
        ds: Dataset procesado
        
    Returns:
        Dict con resultados de validación
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "stats": {}
    }
    
    # Verificar variables requeridas
    required_vars = ["risk_score", "risk_class"]
    for var in required_vars:
        if var not in ds.data_vars:
            results["errors"].append(f"Variable requerida '{var}' no encontrada")
            results["valid"] = False
    
    # Verificar rango de risk_score
    if "risk_score" in ds.data_vars:
        risk_min = float(ds.risk_score.min())
        risk_max = float(ds.risk_score.max())
        
        if risk_min < 0 or risk_max > 100:
            results["errors"].append(f"risk_score fuera de rango [0,100]: [{risk_min:.2f}, {risk_max:.2f}]")
            results["valid"] = False
        
        results["stats"]["risk_score"] = {
            "min": risk_min,
            "max": risk_max,
            "mean": float(ds.risk_score.mean()),
            "std": float(ds.risk_score.std())
        }
    
    # Verificar valores de risk_class
    if "risk_class" in ds.data_vars:
        valid_classes = {"good", "moderate", "bad"}
        unique_classes = set(ds.risk_class.values.flatten())
        invalid_classes = unique_classes - valid_classes
        
        if invalid_classes:
            results["errors"].append(f"Clases de riesgo inválidas: {invalid_classes}")
            results["valid"] = False
        
        # Contar por clase
        class_counts = {}
        for cls in valid_classes:
            count = int((ds.risk_class == cls).sum())
            class_counts[cls] = count
        
        results["stats"]["risk_class"] = class_counts
    
    return results