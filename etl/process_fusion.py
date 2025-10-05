"""
Fase 2 — Fusión, normalización y cálculo del índice AIR Risk Score
CleanSky Los Ángeles - NASA Space Apps Challenge 2024

Este módulo procesa y combina los datasets de la Fase 1 para generar
el índice de riesgo atmosférico unificado.
"""

import os
import pandas as pd
import xarray as xr
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any
import warnings

from utils_math import (
    compute_wind_speed, 
    compute_risk, 
    classify_risk,
    validate_risk_dataset
)

# Configuración de rutas
DATA_RAW = os.path.join(os.path.dirname(__file__), "../data/zarr_store")
DATA_OUT = os.path.join(os.path.dirname(__file__), "../data/processed")

# Crear directorio de salida
os.makedirs(DATA_OUT, exist_ok=True)

def load_dataset_safe(path: str, description: str = "") -> Optional[xr.Dataset]:
    """
    Abre un dataset Zarr/NetCDF de forma segura con manejo de errores.
    
    Args:
        path: Ruta al archivo
        description: Descripción del dataset para logging
        
    Returns:
        Dataset o None si falla
    """
    try:
        print(f"📂 Cargando {description}: {os.path.basename(path)}")
        
        if path.endswith('.zarr'):
            ds = xr.open_zarr(path)
        elif path.endswith(('.nc', '.nc4')):
            ds = xr.open_dataset(path)
        else:
            print(f"⚠️  Formato no reconocido: {path}")
            return None
            
        print(f"✅ {description} cargado: {dict(ds.dims)} variables: {list(ds.data_vars.keys())}")
        return ds
        
    except Exception as e:
        print(f"❌ Error cargando {description} desde {path}: {e}")
        return None

def load_openaq_data() -> Optional[pd.DataFrame]:
    """
    Carga datos de OpenAQ desde archivos Parquet o CSV.
    
    Returns:
        DataFrame con datos de estaciones terrestres o None
    """
    # Intentar diferentes formatos y ubicaciones
    possible_paths = [
        os.path.join(DATA_RAW, "openaq_latest.parquet"),
        os.path.join(DATA_RAW, "openaq_latest.csv"),
        os.path.join(DATA_RAW, "openaq_data.parquet"),
        os.path.join(DATA_RAW, "openaq_data.csv")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                print(f"📂 Cargando OpenAQ: {os.path.basename(path)}")
                
                if path.endswith('.parquet'):
                    df = pd.read_parquet(path)
                else:
                    df = pd.read_csv(path)
                
                print(f"✅ OpenAQ cargado: {len(df)} registros, parámetros: {df['parameter'].unique()}")
                return df
                
            except Exception as e:
                print(f"⚠️  Error cargando {path}: {e}")
                continue
    
    print("⚠️  No se encontraron datos de OpenAQ")
    return None

def interpolate_ground_data(df: pd.DataFrame, target_grid: xr.DataArray, 
                          parameters: list = None) -> Dict[str, xr.DataArray]:
    """
    Interpola datos terrestres de OpenAQ a la rejilla satelital.
    
    Args:
        df: DataFrame con datos de estaciones
        target_grid: Grid de referencia para interpolación
        parameters: Lista de parámetros a interpolar
        
    Returns:
        Dict con DataArrays interpolados por parámetro
    """
    if parameters is None:
        parameters = ["pm25", "no2", "o3", "pm10", "so2", "co"]
    
    interpolated = {}
    
    for param in parameters:
        param_data = df[df["parameter"].str.lower() == param.lower()]
        
        if param_data.empty:
            print(f"⚠️  No hay datos para {param}")
            continue
        
        # Crear DataArray con coordenadas
        try:
            values = param_data["value"].values
            lats = param_data["lat"].values
            lons = param_data["lon"].values
            
            # Crear array temporal con coordenadas de estaciones
            station_data = xr.DataArray(
                values,
                dims=["station"],
                coords={
                    "lat": ("station", lats),
                    "lon": ("station", lons)
                }
            )
            
            # Interpolar a la rejilla objetivo
            interpolated_data = station_data.interp_like(
                target_grid, 
                method="nearest", 
                kwargs={"fill_value": np.nan}
            )
            
            interpolated[param] = interpolated_data
            print(f"✅ {param.upper()} interpolado: {len(param_data)} estaciones → rejilla")
            
        except Exception as e:
            print(f"❌ Error interpolando {param}: {e}")
            continue
    
    return interpolated

def extract_variable_safe(ds: xr.Dataset, var_patterns: list) -> Optional[xr.DataArray]:
    """
    Extrae una variable de un dataset usando patrones de búsqueda.
    
    Args:
        ds: Dataset fuente
        var_patterns: Lista de patrones a buscar en nombres de variables
        
    Returns:
        DataArray o None si no se encuentra
    """
    if ds is None:
        return None
    
    for pattern in var_patterns:
        # Búsqueda exacta
        if pattern in ds.data_vars:
            return ds[pattern]
        
        # Búsqueda por contenido (case-insensitive)
        for var_name in ds.data_vars:
            if pattern.lower() in var_name.lower():
                return ds[var_name]
    
    return None

def process_fusion() -> xr.Dataset:
    """
    Función principal de fusión de datasets.
    
    Returns:
        Dataset unificado con índice de riesgo
    """
    print("🚀 Iniciando fusión de datasets...")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    
    # ========== CARGA DE DATASETS ==========
    
    # Cargar datasets satelitales
    ds_tempo = load_dataset_safe(os.path.join(DATA_RAW, "tempo_no2.zarr"), "TEMPO NO₂")
    ds_merra2 = load_dataset_safe(os.path.join(DATA_RAW, "merra2_meteo.zarr"), "MERRA-2 Meteorología")
    ds_imerg = load_dataset_safe(os.path.join(DATA_RAW, "imerg_precip.zarr"), "IMERG Precipitación")
    
    # Verificar datasets críticos
    if ds_tempo is None:
        print("⚠️  TEMPO no disponible, intentando cargar datos demo...")
        ds_tempo = load_dataset_safe(os.path.join(DATA_RAW, "tempo_demo.zarr"), "TEMPO Demo")
    
    # También probar archivos CSV demo si no hay Zarr
    if ds_tempo is None:
        tempo_csv = os.path.join(DATA_RAW, "tempo_no2_demo.csv")
        if os.path.exists(tempo_csv):
            print("📂 Cargando TEMPO desde CSV demo...")
            df_tempo = pd.read_csv(tempo_csv)
            if not df_tempo.empty:
                # Convertir a xarray usando nombres completos de coordenadas
                ds_tempo = df_tempo.set_index(['latitude', 'longitude']).to_xarray()
                # Renombrar coordenadas para consistencia
                ds_tempo = ds_tempo.rename({'latitude': 'lat', 'longitude': 'lon'})
                print(f"✅ TEMPO CSV cargado: {len(df_tempo)} puntos")
    
    if ds_merra2 is None:
        print("⚠️  MERRA-2 no disponible, intentando cargar datos demo...")
        # Buscar archivo correcto
        merra2_csv = os.path.join(DATA_RAW, "merra2_weather_demo.csv")
        if not os.path.exists(merra2_csv):
            merra2_csv = os.path.join(DATA_RAW, "merra2_meteo_demo.csv")
        
        if os.path.exists(merra2_csv):
            print("📂 Cargando MERRA-2 desde CSV demo...")
            df_merra2 = pd.read_csv(merra2_csv)
            if not df_merra2.empty:
                ds_merra2 = df_merra2.set_index(['latitude', 'longitude']).to_xarray()
                # Renombrar coordenadas para consistencia
                ds_merra2 = ds_merra2.rename({'latitude': 'lat', 'longitude': 'lon'})
                print(f"✅ MERRA-2 CSV cargado: {len(df_merra2)} puntos")
    
    # Cargar datos terrestres
    df_openaq = load_openaq_data()
    
    # ========== VERIFICAR DISPONIBILIDAD ==========
    
    available_datasets = []
    if ds_tempo: available_datasets.append("TEMPO")
    if ds_merra2: available_datasets.append("MERRA-2")
    if ds_imerg: available_datasets.append("IMERG")
    if df_openaq is not None: available_datasets.append("OpenAQ")
    
    print(f"📊 Datasets disponibles: {', '.join(available_datasets)}")
    
    if not available_datasets:
        raise RuntimeError("❌ No hay datasets disponibles para procesar")
    
    # ========== EXTRACCIÓN DE VARIABLES ==========
    
    print("🔍 Extrayendo variables...")
    
    # Variables satelitales
    no2_sat = extract_variable_safe(ds_tempo, ["no2", "NO2", "nitrogen_dioxide"])
    temp = extract_variable_safe(ds_merra2, ["T2M", "temp", "temperature"])
    u_wind = extract_variable_safe(ds_merra2, ["U2M", "u", "u_wind"])
    v_wind = extract_variable_safe(ds_merra2, ["V2M", "v", "v_wind"])
    rain = extract_variable_safe(ds_imerg, ["precip", "precipitation", "rain"])
    
    # ========== CREAR DATASET BASE ==========
    
    print("🧩 Construyendo dataset base...")
    
    base_vars = {}
    
    # NO₂ satelital
    if no2_sat is not None:
        base_vars["no2"] = no2_sat
        print(f"   ✅ NO₂: {no2_sat.dims} ({no2_sat.attrs.get('units', 'molec/cm²')})")
    
    # Meteorología
    if temp is not None:
        base_vars["temp"] = temp
        print(f"   ✅ Temperatura: {temp.dims} ({temp.attrs.get('units', 'K')})")
    
    if u_wind is not None and v_wind is not None:
        wind_speed = compute_wind_speed(u_wind, v_wind)
        base_vars["wind"] = wind_speed
        print(f"   ✅ Viento: calculado desde U/V componentes ({wind_speed.dims})")
    
    # Precipitación (opcional)
    if rain is not None:
        base_vars["rain"] = rain
        print(f"   ✅ Precipitación: {rain.dims} ({rain.attrs.get('units', 'mm/hr')})")
    
    # Crear dataset base
    if not base_vars:
        raise RuntimeError("❌ No se pudieron extraer variables satelitales")
    
    base_ds = xr.Dataset(base_vars)
    
    # ========== INTERPOLACIÓN DE DATOS TERRESTRES ==========
    
    if df_openaq is not None:
        print("🌍 Interpolando datos terrestres de OpenAQ...")
        
        # Usar la primera variable disponible como referencia para la rejilla
        reference_var = list(base_vars.values())[0]
        
        # Interpolar datos terrestres
        ground_data = interpolate_ground_data(df_openaq, reference_var)
        
        # Agregar al dataset base
        for param, data in ground_data.items():
            # Si ya existe la variable satelital, combinar
            if param in base_ds.data_vars:
                print(f"   🔄 Combinando {param} satelital + terrestre")
                # Usar datos terrestres donde estén disponibles, satelitales como fallback
                combined = data.fillna(base_ds[param])
                base_ds[param] = combined
            else:
                base_ds[param] = data
            
            print(f"   ✅ {param.upper()}: datos terrestres integrados")
    
    # ========== CÁLCULO DEL ÍNDICE DE RIESGO ==========
    
    print("🧮 Calculando índice AIR Risk Score...")
    
    # Extraer variables para el cálculo
    no2_final = base_ds.get("no2")
    o3_final = base_ds.get("o3") 
    pm25_final = base_ds.get("pm25")
    temp_final = base_ds.get("temp")
    wind_final = base_ds.get("wind")
    aerosol_final = base_ds.get("aerosol")  # Opcional
    rain_final = base_ds.get("rain")  # Opcional
    
    # Verificar que tengamos al menos algunas variables
    available_vars = []
    if no2_final is not None: available_vars.append("NO₂")
    if o3_final is not None: available_vars.append("O₃")
    if pm25_final is not None: available_vars.append("PM2.5")
    if temp_final is not None: available_vars.append("Temperatura")
    if wind_final is not None: available_vars.append("Viento")
    
    print(f"   📊 Variables disponibles para riesgo: {', '.join(available_vars)}")
    
    if len(available_vars) < 2:
        print("⚠️  Pocas variables disponibles. Generando índice básico...")
    
    # Calcular el índice de riesgo
    try:
        risk_score = compute_risk(
            no2=no2_final,
            o3=o3_final, 
            pm25=pm25_final,
            temp=temp_final,
            wind=wind_final,
            aerosol=aerosol_final,
            rain=rain_final
        )
        
        risk_class = classify_risk(risk_score)
        
        # Agregar al dataset
        base_ds["risk_score"] = risk_score
        base_ds["risk_class"] = risk_class
        
        print(f"   ✅ Risk Score: [{float(risk_score.min()):.1f}, {float(risk_score.max()):.1f}]")
        print(f"   ✅ Risk Class: {np.unique(risk_class.values)}")
        
    except Exception as e:
        print(f"❌ Error calculando riesgo: {e}")
        raise
    
    # ========== AÑADIR METADATOS ==========
    
    base_ds.attrs.update({
        "title": "CleanSky Los Angeles - AIR Risk Score Dataset",
        "description": "Unified atmospheric risk assessment combining satellite and ground-based observations",
        "created": datetime.now().isoformat(),
        "phase": "2",
        "spatial_resolution": "0.05 degrees",
        "data_sources": ", ".join(available_datasets),
        "risk_calculation": "Weighted combination of NO₂, O₃, PM2.5, temperature, and wind dispersion factors"
    })
    
    # ========== GUARDAR RESULTADO ==========
    
    out_path = os.path.join(DATA_OUT, "airs_risk.zarr")
    print(f"💾 Guardando dataset unificado...")
    
    try:
        # Eliminar archivo existente si existe
        if os.path.exists(out_path):
            import shutil
            shutil.rmtree(out_path)
        
        base_ds.to_zarr(out_path, mode="w")
        print(f"✅ Dataset final guardado en {out_path}")
        
        # Mostrar estadísticas finales
        file_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                       for dirpath, dirnames, filenames in os.walk(out_path)
                       for filename in filenames) / (1024 * 1024)
        
        print(f"📊 Estadísticas finales:")
        print(f"   • Dimensiones: {dict(base_ds.dims)}")
        print(f"   • Variables: {len(base_ds.data_vars)}")
        print(f"   • Tamaño: {file_size:.1f} MB")
        
    except Exception as e:
        print(f"❌ Error guardando dataset: {e}")
        raise
    
    # ========== VALIDACIÓN ==========
    
    print("🔍 Validando dataset final...")
    validation_results = validate_risk_dataset(base_ds)
    
    if validation_results["valid"]:
        print("✅ Validación exitosa")
        if validation_results["stats"]:
            stats = validation_results["stats"]
            if "risk_score" in stats:
                rs = stats["risk_score"]
                print(f"   • Risk Score: μ={rs['mean']:.1f}, σ={rs['std']:.1f}")
            if "risk_class" in stats:
                rc = stats["risk_class"]
                print(f"   • Risk Classes: {rc}")
    else:
        print("❌ Errores en validación:")
        for error in validation_results["errors"]:
            print(f"   • {error}")
    
    return base_ds
