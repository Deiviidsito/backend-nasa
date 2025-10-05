"""
Gestión del dataset NetCDF y operaciones con xarray
"""
import xarray as xr
import os
import numpy as np
from typing import Dict, Any, Optional

DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/processed/airs_risk.nc")
_ds_cache = None

def get_dataset() -> xr.Dataset:
    """Carga el dataset una sola vez en memoria (singleton)."""
    global _ds_cache
    if _ds_cache is None:
        print("🛰️ Cargando dataset airs_risk.nc en memoria...")
        try:
            _ds_cache = xr.open_dataset(DATA_PATH)
            print(f"✅ Dataset cargado: {_ds_cache.dims}")
        except Exception as e:
            print(f"❌ Error cargando dataset: {e}")
            raise
    return _ds_cache

def get_risk_at_point(lat: float, lon: float) -> Dict[str, Any]:
    """Interpola el risk_score y variables asociadas para un punto geográfico."""
    ds = get_dataset()
    
    try:
        # Usar el método más cercano si no está disponible scipy
        data_point = ds.sel(lat=lat, lon=lon, method='nearest')
        
        # Extraer valores y manejar posibles NaN
        risk_score = float(data_point["risk_score"].values)
        risk_class = determine_risk_class(risk_score)
        
        result = {
            "latitude": float(lat),
            "longitude": float(lon),
            "risk_score": risk_score if not np.isnan(risk_score) else 0.0,
            "risk_class": risk_class,
        }
        
        # Agregar variables opcionales si existen
        optional_vars = ["no2", "o3", "pm25", "temp", "wind"]
        for var in optional_vars:
            if var in data_point:
                value = float(data_point[var].values)
                result[var] = value if not np.isnan(value) else None
            else:
                result[var] = None
        
        return result
        
    except Exception as e:
        print(f"❌ Error interpolando punto ({lat}, {lon}): {e}")
        # Retornar valores por defecto en caso de error
        return {
            "latitude": float(lat),
            "longitude": float(lon),
            "risk_score": 0.0,
            "risk_class": "unknown",
            "no2": None,
            "o3": None,
            "pm25": None,
            "temp": None,
            "wind": None,
        }

def determine_risk_class(risk_score: float) -> str:
    """Determina la clase de riesgo basada en el score numérico."""
    if np.isnan(risk_score):
        return "unknown"
    elif risk_score >= 67:
        return "high"
    elif risk_score >= 34:
        return "moderate"
    else:
        return "low"

def get_dataset_bounds() -> Dict[str, float]:
    """Retorna los límites geográficos del dataset."""
    ds = get_dataset()
    return {
        "lat_min": float(ds.lat.min().values),
        "lat_max": float(ds.lat.max().values),
        "lon_min": float(ds.lon.min().values),
        "lon_max": float(ds.lon.max().values),
    }

def get_dataset_info() -> Dict[str, Any]:
    """Retorna información general del dataset."""
    ds = get_dataset()
    return {
        "dimensions": dict(ds.dims),
        "variables": list(ds.data_vars.keys()),
        "bounds": get_dataset_bounds(),
        "total_points": int(ds.lat.size * ds.lon.size)
    }