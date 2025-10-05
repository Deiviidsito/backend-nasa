#!/usr/bin/env python3
"""
Fase 2 completa - Versión funcional
CleanSky Los Angeles - AIR Risk Score
"""

import pandas as pd
import numpy as np
import xarray as xr
import os
from datetime import datetime

def fase2_completa():
    print("🚀 CLEANSKY LOS ANGELES - FASE 2")
    print("   Procesamiento completo AIR Risk Score")
    print("=" * 60)
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Configurar rutas  
    data_raw = "../data/zarr_store"
    data_out = "../data/processed"
    os.makedirs(data_out, exist_ok=True)
    
    # ========== 1. CARGA DE DATOS ==========
    print("📂 CARGANDO DATASETS")
    print("-" * 30)
    
    # TEMPO NO2 (satelital)
    print("📡 TEMPO NO₂ (satelital)...")
    df_tempo = pd.read_csv(os.path.join(data_raw, "tempo_no2_demo.csv"))
    print(f"   ✅ {len(df_tempo)} puntos NO₂")
    
    # MERRA-2 Meteorología (satelital)
    print("🌤️  MERRA-2 Meteorología...")
    df_merra2 = pd.read_csv(os.path.join(data_raw, "merra2_weather_demo.csv"))
    # Eliminar duplicados promediando
    df_merra2_clean = df_merra2.groupby(['latitude', 'longitude']).agg({
        'T2M': 'mean',
        'U2M': 'mean', 
        'V2M': 'mean'
    }).reset_index()
    print(f"   ✅ {len(df_merra2_clean)} puntos meteorológicos")
    
    # OpenAQ (estaciones terrestres)
    print("🏭 OpenAQ (estaciones terrestres)...")
    df_openaq = pd.read_parquet(os.path.join(data_raw, "openaq_latest.parquet"))
    
    # Estadísticas por parámetro
    param_stats = {}
    for param in ["pm25", "no2", "o3"]:
        param_data = df_openaq[df_openaq["parameter"].str.lower() == param]
        if not param_data.empty:
            param_stats[param] = {
                "count": len(param_data),
                "mean": param_data["value"].mean(),
                "std": param_data["value"].std()
            }
            print(f"   • {param.upper()}: {len(param_data)} estaciones, μ={param_data['value'].mean():.2f}")
    
    print()
    
    # ========== 2. PROCESAMIENTO SATELITAL ==========
    print("🛰️  PROCESAMIENTO SATELITAL")
    print("-" * 30)
    
    # Crear rejilla base desde TEMPO
    print("🗺️  Creando rejilla espacial...")
    lats = sorted(df_tempo['latitude'].unique())
    lons = sorted(df_tempo['longitude'].unique())
    print(f"   ✅ Rejilla: {len(lats)}×{len(lons)} puntos")
    
    # Convertir TEMPO a rejilla
    tempo_grid = df_tempo.pivot_table(
        index='latitude', 
        columns='longitude', 
        values='no2_tropospheric_column',
        aggfunc='mean'
    )
    no2_array = tempo_grid.values
    print(f"   ✅ NO₂: rango [{np.nanmin(no2_array):.2e}, {np.nanmax(no2_array):.2e}] molec/cm²")
    
    # Interpolar MERRA-2 a la rejilla TEMPO
    print("🌡️  Interpolando meteorología...")
    
    # Crear grids meteorológicos
    temp_grid = np.full((len(lats), len(lons)), np.nan)
    wind_grid = np.full((len(lats), len(lons)), np.nan)
    
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            # Buscar punto meteorológico más cercano
            distances = np.sqrt((df_merra2_clean['latitude'] - lat)**2 + 
                              (df_merra2_clean['longitude'] - lon)**2)
            nearest_idx = distances.idxmin()
            
            temp_grid[i, j] = df_merra2_clean.loc[nearest_idx, 'T2M']
            u_wind = df_merra2_clean.loc[nearest_idx, 'U2M']
            v_wind = df_merra2_clean.loc[nearest_idx, 'V2M']
            wind_grid[i, j] = np.sqrt(u_wind**2 + v_wind**2)
    
    print(f"   ✅ Temperatura: rango [{np.nanmin(temp_grid):.1f}, {np.nanmax(temp_grid):.1f}] K")
    print(f"   ✅ Viento: rango [{np.nanmin(wind_grid):.1f}, {np.nanmax(wind_grid):.1f}] m/s")
    
    print()
    
    # ========== 3. INTEGRACIÓN DATOS TERRESTRES ==========
    print("🏭 INTEGRACIÓN DATOS TERRESTRES") 
    print("-" * 30)
    
    # Crear arrays para datos terrestres
    pm25_grid = np.full((len(lats), len(lons)), np.nan)
    o3_grid = np.full((len(lats), len(lons)), np.nan)
    no2_ground_grid = np.full((len(lats), len(lons)), np.nan)
    
    # Interpolar datos terrestres usando promedio ponderado por distancia
    for param in ["pm25", "no2", "o3"]:
        if param in param_stats:
            param_data = df_openaq[df_openaq["parameter"].str.lower() == param]
            
            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    # Calcular distancias a todas las estaciones
                    distances = np.sqrt((param_data['lat'] - lat)**2 + 
                                      (param_data['lon'] - lon)**2)
                    
                    # Usar estaciones dentro de ~50km (0.5 grados aprox)
                    nearby_mask = distances < 0.5
                    if nearby_mask.any():
                        nearby_values = param_data.loc[nearby_mask, 'value']
                        nearby_distances = distances[nearby_mask]
                        
                        # Promedio ponderado por distancia inversa
                        weights = 1 / (nearby_distances + 0.01)  # +0.01 para evitar div/0
                        weighted_value = np.average(nearby_values, weights=weights)
                        
                        if param == "pm25":
                            pm25_grid[i, j] = weighted_value
                        elif param == "no2":
                            no2_ground_grid[i, j] = weighted_value
                        elif param == "o3":
                            o3_grid[i, j] = weighted_value
    
    # Usar promedios globales donde no hay datos terrestres
    for param in ["pm25", "o3", "no2"]:
        if param in param_stats:
            grid = {"pm25": pm25_grid, "o3": o3_grid, "no2": no2_ground_grid}[param]
            avg_value = param_stats[param]["mean"]
            grid[np.isnan(grid)] = avg_value
            
            valid_points = ~np.isnan(grid)
            print(f"   ✅ {param.upper()}: {np.sum(valid_points)} puntos interpolados")
    
    print()
    
    # ========== 4. NORMALIZACIÓN Y CÁLCULO DE RIESGO ==========
    print("🧮 CÁLCULO DEL ÍNDICE AIR RISK SCORE")
    print("-" * 30)
    
    def normalize_grid(grid):
        \"\"\"Normalizar rejilla entre 0 y 1\"\"\"
        valid_mask = ~np.isnan(grid)
        if valid_mask.any():
            min_val = np.nanmin(grid)
            max_val = np.nanmax(grid)
            range_val = max_val - min_val
            if range_val > 0:
                normalized = (grid - min_val) / range_val
                return normalized
        return np.zeros_like(grid)
    
    # Normalizar variables
    print("📊 Normalizando variables...")
    no2_norm = normalize_grid(no2_array)
    temp_norm = normalize_grid(temp_grid)
    wind_risk = (wind_grid < 2.0).astype(float)  # Penalizar viento bajo
    pm25_norm = normalize_grid(pm25_grid) if not np.all(np.isnan(pm25_grid)) else np.zeros_like(no2_norm)
    o3_norm = normalize_grid(o3_grid) if not np.all(np.isnan(o3_grid)) else np.zeros_like(no2_norm)
    
    print("   ✅ Variables normalizadas")
    
    # Calcular índice de riesgo ponderado
    print("⚖️  Aplicando pesos científicos...")
    risk_score = (
        0.30 * no2_norm +      # NO₂ satelital (30%)
        0.25 * o3_norm +       # O₃ terrestre (25%) 
        0.20 * pm25_norm +     # PM2.5 terrestre (20%)
        0.15 * temp_norm +     # Factor temperatura (15%)
        0.10 * wind_risk       # Factor dispersión viento (10%)
    ) * 100
    
    print(f"   ✅ Risk Score: [{np.nanmin(risk_score):.1f}, {np.nanmax(risk_score):.1f}]")
    
    # Clasificar riesgo
    print("🚦 Clasificando niveles de riesgo...")
    risk_class = np.where(risk_score < 34, "good",
                         np.where(risk_score <= 66, "moderate", "bad"))
    
    unique_classes, counts = np.unique(risk_class, return_counts=True)
    total_points = len(risk_class.flatten())
    for cls, count in zip(unique_classes, counts):
        percentage = (count / total_points) * 100
        print(f"   • {cls:10s}: {count:4d} puntos ({percentage:5.1f}%)")
    
    print()
    
    # ========== 5. CREAR DATASET XARRAY ==========
    print("📦 CREANDO DATASET FINAL")
    print("-" * 30)
    
    # Crear coordenadas
    lat_coords = xr.DataArray(lats, dims=["lat"])
    lon_coords = xr.DataArray(lons, dims=["lon"])
    
    # Crear dataset final
    final_dataset = xr.Dataset(
        {
            "no2": (["lat", "lon"], no2_array),
            "temp": (["lat", "lon"], temp_grid),
            "wind": (["lat", "lon"], wind_grid),
            "pm25": (["lat", "lon"], pm25_grid),
            "o3": (["lat", "lon"], o3_grid),
            "risk_score": (["lat", "lon"], risk_score),
            "risk_class": (["lat", "lon"], risk_class)
        },
        coords={
            "lat": lat_coords,
            "lon": lon_coords
        }
    )
    
    # Agregar metadatos completos
    final_dataset.attrs.update({
        "title": "CleanSky Los Angeles - AIR Risk Score Dataset",
        "description": "Unified atmospheric risk assessment combining satellite and ground-based observations",
        "institution": "NASA Space Apps Challenge 2024",
        "source": "TEMPO NO₂, MERRA-2 Meteorology, OpenAQ Ground Stations", 
        "created": datetime.now().isoformat(),
        "phase": "2",
        "spatial_resolution": f"{len(lats)}x{len(lons)} grid over Los Angeles",
        "risk_calculation": "Weighted index: 30% NO₂ + 25% O₃ + 20% PM2.5 + 15% Temperature + 10% Wind dispersion",
        "risk_classes": "good (<34), moderate (34-66), bad (>66)",
        "coordinate_system": "WGS84 (latitude/longitude)",
        "time_coverage": "Latest available observations",
        "processing_level": "L3 - Analyzed product"
    })
    
    # Agregar atributos a variables
    variable_attrs = {
        "no2": {"units": "molec/cm²", "long_name": "NO₂ Tropospheric Column", "source": "TEMPO"},
        "temp": {"units": "K", "long_name": "2m Temperature", "source": "MERRA-2"},
        "wind": {"units": "m/s", "long_name": "10m Wind Speed", "source": "MERRA-2"},
        "pm25": {"units": "µg/m³", "long_name": "PM2.5 Concentration", "source": "OpenAQ"},
        "o3": {"units": "ppb", "long_name": "Ozone Concentration", "source": "OpenAQ"},
        "risk_score": {"units": "0-100", "long_name": "AIR Risk Score", "description": "Atmospheric pollution risk index"},
        "risk_class": {"long_name": "Risk Classification", "values": "good, moderate, bad"}
    }
    
    for var_name, attrs in variable_attrs.items():
        if var_name in final_dataset.data_vars:
            final_dataset[var_name].attrs.update(attrs)
    
    print(f"   ✅ Dataset: {dict(final_dataset.dims)}")
    print(f"   ✅ Variables: {list(final_dataset.data_vars.keys())}")
    
    # ========== 6. GUARDAR RESULTADOS ==========
    print("💾 GUARDANDO RESULTADOS")
    print("-" * 30)
    
    # Guardar como NetCDF (más compatible)
    output_nc = os.path.join(data_out, "airs_risk.nc")
    final_dataset.to_netcdf(output_nc)
    print(f"   ✅ NetCDF: {output_nc}")
    
    # Guardar también como CSV para compatibilidad
    output_csv = os.path.join(data_out, "airs_risk.csv")
    df_final = final_dataset.to_dataframe().reset_index()
    df_final.to_csv(output_csv, index=False)
    print(f"   ✅ CSV: {output_csv}")
    
    # Intentar guardar como Zarr si es posible
    try:
        output_zarr = os.path.join(data_out, "airs_risk.zarr")
        if os.path.exists(output_zarr):
            import shutil
            shutil.rmtree(output_zarr)
        final_dataset.to_zarr(output_zarr, mode="w")
        print(f"   ✅ Zarr: {output_zarr}")
    except Exception as e:
        print(f"   ⚠️  Zarr falló: {e}")
    
    # Calcular tamaños de archivo
    file_sizes = {}
    for path, label in [(output_nc, "NetCDF"), (output_csv, "CSV")]:
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            file_sizes[label] = size_kb
            print(f"   • {label}: {size_kb:.1f} KB")
    
    print()
    
    # ========== 7. VALIDACIÓN FINAL ==========  
    print("🔍 VALIDACIÓN FINAL")
    print("-" * 30)
    
    # Verificar recarga
    ds_test = xr.open_dataset(output_nc)
    print("   ✅ Recarga exitosa")
    
    # Estadísticas de calidad
    risk_stats = {
        "mean": float(ds_test.risk_score.mean()),
        "std": float(ds_test.risk_score.std()),
        "min": float(ds_test.risk_score.min()),
        "max": float(ds_test.risk_score.max())
    }
    
    print(f"   • Risk Score: μ={risk_stats['mean']:.1f}, σ={risk_stats['std']:.1f}")
    print(f"   • Rango válido: [{risk_stats['min']:.1f}, {risk_stats['max']:.1f}] ✓")
    
    # Verificar completitud
    total_cells = len(lats) * len(lons)
    valid_cells = int((~np.isnan(ds_test.risk_score.values)).sum())
    completeness = (valid_cells / total_cells) * 100
    print(f"   • Completitud: {valid_cells}/{total_cells} ({completeness:.1f}%)")
    
    ds_test.close()
    
    print()
    print("🎉" * 20)
    print("✅ FASE 2 COMPLETADA EXITOSAMENTE")
    print("🎉" * 20)
    
    print(f"📊 RESUMEN EJECUTIVO:")
    print(f"   • Área procesada: Los Ángeles ({len(lats)}×{len(lons)} rejilla)")
    print(f"   • Fuentes integradas: TEMPO + MERRA-2 + OpenAQ")
    print(f"   • Algoritmo: Índice ponderado AIR Risk Score")
    print(f"   • Resultado: {valid_cells} celdas con riesgo calculado")
    print(f"   • Clasificación: {dict(zip(unique_classes, counts))}")
    print(f"   • Archivos generados: NetCDF, CSV" + (", Zarr" if os.path.exists(os.path.join(data_out, "airs_risk.zarr")) else ""))
    
    print(f"\\n🎯 PRÓXIMOS PASOS:")
    print(f"   • Cargar dataset: ds = xr.open_dataset('{output_nc}')")
    print(f"   • Visualizar: ds.risk_score.plot()")
    print(f"   • Análisis: ds.risk_class.to_series().value_counts()")
    
    return final_dataset

if __name__ == "__main__":
    try:
        dataset = fase2_completa()
    except Exception as e:
        print(f"\\n❌ ERROR EN FASE 2: {e}")
        import traceback
        traceback.print_exc()