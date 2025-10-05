"""
Descarga las mediciones más recientes de PM2.5, NO2 y O3 en Los Ángeles desde OpenAQ.
"""
import requests
import pandas as pd
import os
from typing import Optional, List, Dict, Any
try:
    from .utils import (
        BBOX_LA, DATA_DIR, OPENAQ_CONFIG,
        ensure_data_dirs, format_bbox_for_openaq,
        log_info, log_error, log_success
    )
except ImportError:
    from utils import (
        BBOX_LA, DATA_DIR, OPENAQ_CONFIG,
        ensure_data_dirs, format_bbox_for_openaq,
        log_info, log_error, log_success
    )

def fetch_latest_openaq(
    bbox: tuple = BBOX_LA,
    parameters: List[str] = None
) -> Optional[str]:
    """
    Descargar mediciones recientes de OpenAQ v3 para Los Ángeles.
    
    Args:
        bbox: Bounding box (west, south, east, north)
        parameters: Lista de parámetros a descargar (default: pm25, no2, o3)
        
    Returns:
        Path del archivo parquet creado o None si falla
    """
    ensure_data_dirs()
    
    if parameters is None:
        parameters = OPENAQ_CONFIG["parameters"]
    
    bbox_str = format_bbox_for_openaq(bbox)
    log_info(f"Descargando datos OpenAQ v3 para bbox: {bbox_str}, parámetros: {parameters}")
    
    try:
        # Headers de autenticación
        headers = OPENAQ_CONFIG.get("headers", {})
        
        # Paso 1: Obtener ubicaciones en el área de Los Ángeles
        locations_url = OPENAQ_CONFIG["api_url"]
        locations_params = {
            "bbox": bbox_str,
            "limit": 1000,
            "sort": "desc",
            "order_by": "lastUpdated"
        }
        
        log_info(f"1️⃣ Obteniendo ubicaciones: {locations_url}")
        log_info(f"Headers disponibles: {list(headers.keys())}")
        
        locations_response = requests.get(locations_url, params=locations_params, headers=headers, timeout=30)
        locations_response.raise_for_status()
        
        locations_data = locations_response.json()
        
        if "results" not in locations_data:
            log_error("Respuesta sin campo 'results' en ubicaciones")
            return None
        
        locations = locations_data["results"]
        
        if not locations:
            log_error("No se encontraron ubicaciones en el área especificada")
            return None
        
        log_info(f"✅ Encontradas {len(locations)} ubicaciones")
        
        # Paso 2: Obtener mediciones más recientes para cada ubicación
        all_measurements = []
        
        for location in locations[:20]:  # Limitar a 20 ubicaciones para no sobrecargar
            location_id = location.get("id")
            location_name = location.get("name", "Unknown")
            
            if not location_id:
                continue
            
            try:
                # Usar el endpoint de mediciones más recientes por ubicación
                latest_url = f"https://api.openaq.org/v3/locations/{location_id}/latest"
                
                log_info(f"2️⃣ Obteniendo mediciones para: {location_name} (ID: {location_id})")
                
                measurements_response = requests.get(latest_url, headers=headers, timeout=15)
                measurements_response.raise_for_status()
                
                measurements_data = measurements_response.json()
                
                if "results" not in measurements_data:
                    continue
                
                # Procesar mediciones de esta ubicación
                for measurement in measurements_data["results"]:
                    param = measurement.get("parameter", {}).get("name", "").lower()
                    
                    # Filtrar por parámetros de interés
                    if param not in parameters:
                        continue
                    
                    # Extraer datos de la medición
                    row = {
                        "timestamp": measurement.get("datetime"),
                        "location_id": location_id,
                        "location_name": location_name,
                        "parameter": param,
                        "value": measurement.get("value"),
                        "unit": measurement.get("parameter", {}).get("units", ""),
                        "latitude": location.get("coordinates", {}).get("latitude"),
                        "longitude": location.get("coordinates", {}).get("longitude"),
                        "country": location.get("country", {}).get("name", ""),
                        "city": location.get("city", "")
                    }
                    
                    all_measurements.append(row)
                
            except Exception as e:
                log_error(f"Error procesando ubicación {location_name}: {str(e)}")
                continue
        
        if not all_measurements:
            log_error("No se obtuvieron mediciones válidas")
            return None
        
        log_info(f"✅ Procesadas {len(all_measurements)} mediciones")
        
        # Paso 3: Crear DataFrame y guardar
        df = pd.DataFrame(all_measurements)
        
        # Filtrar y limpiar datos
        df = df.dropna(subset=['value', 'latitude', 'longitude'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        output_path = DATA_DIR / OPENAQ_CONFIG["output_path"]
        
        # Guardar como Parquet
        df.to_parquet(output_path, index=False)
        
        log_success(f"✅ OpenAQ: {len(df)} mediciones guardadas en {output_path}")
        
        # Mostrar resumen
        summary = df.groupby('parameter')['value'].agg(['count', 'mean', 'min', 'max']).round(2)
        log_info(f"📊 Resumen por parámetro:\n{summary}")
        
        return str(output_path)
                    
                    value = measurement.get("value")
                    unit = measurement.get("unit")
                    last_updated = measurement.get("lastUpdated")
                    
                    if value is None:
                        continue
                    
                    rows.append({
                        "station_id": station_id,
                        "station_name": station_name,
                        "lat": lat,
                        "lon": lon,
                        "parameter": param,
                        "value": float(value),
                        "unit": unit,
                        "lastUpdated": last_updated,
                        "country": location_info.get("country", ""),
                        "city": location_info.get("city", ""),
                        "isMobile": location_info.get("isMobile", False),
                        "isAnalysis": location_info.get("isAnalysis", False)
                    })
                    
            except Exception as e:
                log_error(f"Error procesando registro OpenAQ: {e}")
                continue
        
        if not rows:
            log_error("No se pudieron procesar datos válidos de OpenAQ")
            return None
        
        # Crear DataFrame
        df = pd.DataFrame(rows)
        
        # Limpiar y validar datos
        df = df.dropna(subset=["value", "lat", "lon"])
        df = df[df["value"] >= 0]  # Eliminar valores negativos
        
        # Agregar metadatos
        df["download_timestamp"] = pd.Timestamp.now()
        df["bbox_used"] = bbox_str
        
        # Estadísticas por parámetro
        param_stats = df.groupby("parameter").agg({
            "value": ["count", "mean", "min", "max"],
            "station_id": "nunique"
        }).round(2)
        
        log_info("Estadísticas por parámetro:")
        for param in param_stats.index:
            stats = param_stats.loc[param]
            log_info(f"  {param}: {stats[('value', 'count')]} mediciones, "
                    f"{stats[('station_id', 'nunique')]} estaciones, "
                    f"promedio: {stats[('value', 'mean')]}")
        
        # Guardar como Parquet
        output_path = DATA_DIR / OPENAQ_CONFIG["output_path"]
        df.to_parquet(output_path, index=False)
        
        log_success(f"OpenAQ guardado en {output_path}")
        log_info(f"Total registros: {len(df)}, estaciones únicas: {df['station_id'].nunique()}")
        
        return str(output_path)
        
    except requests.RequestException as e:
        log_error(f"Error de conexión con OpenAQ API: {e}")
        return None
    except Exception as e:
        log_error(f"Error procesando datos OpenAQ: {e}")
        return None

def validate_openaq_data(parquet_path: str) -> bool:
    """Validar que los datos OpenAQ se guardaron correctamente."""
    try:
        df = pd.read_parquet(parquet_path)
        
        # Verificar columnas esenciales
        required_cols = ["station_id", "lat", "lon", "parameter", "value"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            log_error(f"Columnas faltantes en OpenAQ: {missing_cols}")
            return False
        
        # Verificar que hay datos
        if len(df) == 0:
            log_error("DataFrame OpenAQ está vacío")
            return False
        
        # Verificar coordenadas válidas para LA
        west, south, east, north = BBOX_LA
        valid_coords = (
            (df["lat"] >= south) & (df["lat"] <= north) &
            (df["lon"] >= west) & (df["lon"] <= east)
        )
        
        if not valid_coords.all():
            invalid_count = (~valid_coords).sum()
            log_error(f"{invalid_count} registros con coordenadas fuera del bbox")
        
        # Verificar parámetros esperados
        available_params = df["parameter"].unique()
        expected_params = OPENAQ_CONFIG["parameters"]
        
        log_info(f"Parámetros disponibles: {list(available_params)}")
        log_info(f"Parámetros esperados: {expected_params}")
        
        log_success(f"Validación OpenAQ exitosa: {len(df)} registros válidos")
        return True
        
    except Exception as e:
        log_error(f"Error validando OpenAQ: {e}")
        return False

def get_openaq_summary(parquet_path: str) -> Dict[str, Any]:
    """Obtener resumen de los datos OpenAQ."""
    try:
        df = pd.read_parquet(parquet_path)
        
        summary = {
            "total_records": len(df),
            "unique_stations": df["station_id"].nunique(),
            "parameters": list(df["parameter"].unique()),
            "date_range": {
                "min": df["lastUpdated"].min() if "lastUpdated" in df else None,
                "max": df["lastUpdated"].max() if "lastUpdated" in df else None
            },
            "bbox_coverage": {
                "lat_min": df["lat"].min(),
                "lat_max": df["lat"].max(),
                "lon_min": df["lon"].min(),
                "lon_max": df["lon"].max()
            },
            "parameter_stats": df.groupby("parameter")["value"].agg(["count", "mean", "min", "max"]).to_dict()
        }
        
        return summary
        
    except Exception as e:
        log_error(f"Error generando resumen OpenAQ: {e}")
        return {}

if __name__ == "__main__":
    # Test standalone
    result = fetch_latest_openaq()
    if result:
        validate_openaq_data(result)
        summary = get_openaq_summary(result)
        print("Resumen:", summary)
