#!/usr/bin/env python3
"""
Implementación simple de Fase 2 sin zarr (usando NetCDF)
"""

import pandas as pd
import xarray as xr
import numpy as np
import os
from datetime import datetime

def simple_risk_calculation():
    print("🚀 FASE 2 - Implementación simple")
    print("=" * 50)
    
    # Configurar rutas
    data_raw = "../data/zarr_store"
    data_out = "../data/processed"
    os.makedirs(data_out, exist_ok=True)
    
    # 1. Cargar TEMPO NO2
    print("1️⃣ Cargando datos TEMPO...")
    tempo_csv = os.path.join(data_raw, "tempo_no2_demo.csv")
    df_tempo = pd.read_csv(tempo_csv)
    
    # Convertir a xarray
    ds_tempo = df_tempo.set_index(['latitude', 'longitude']).to_xarray()
    ds_tempo = ds_tempo.rename({'latitude': 'lat', 'longitude': 'lon'})
    no2 = ds_tempo['no2_tropospheric_column']
    print(f"   ✅ NO₂: {dict(ds_tempo.dims)}, rango [{float(no2.min()):.2e}, {float(no2.max()):.2e}]")
    
    # 2. Cargar MERRA-2
    print("2️⃣ Cargando datos MERRA-2...")
    merra2_csv = os.path.join(data_raw, "merra2_weather_demo.csv")
    df_merra2 = pd.read_csv(merra2_csv)
    
    # Eliminar duplicados tomando el promedio por coordenada
    print(f"   • Registros originales: {len(df_merra2)}")
    df_merra2_clean = df_merra2.groupby(['latitude', 'longitude']).agg({
        'T2M': 'mean',
        'U2M': 'mean', 
        'V2M': 'mean'
    }).reset_index()
    print(f"   • Después de promediar duplicados: {len(df_merra2_clean)}")
    
    ds_merra2 = df_merra2_clean.set_index(['latitude', 'longitude']).to_xarray()
    ds_merra2 = ds_merra2.rename({'latitude': 'lat', 'longitude': 'lon'})
    
    temp = ds_merra2['T2M']
    u_wind = ds_merra2['U2M']
    v_wind = ds_merra2['V2M']
    wind_speed = np.sqrt(u_wind**2 + v_wind**2)
    print(f"   ✅ Meteorología: T={float(temp.mean()):.1f}K, Wind={float(wind_speed.mean()):.1f}m/s")
    
    # 3. Cargar OpenAQ (datos terrestres)
    print("3️⃣ Cargando datos OpenAQ...")
    openaq_path = os.path.join(data_raw, "openaq_latest.parquet")
    df_openaq = pd.read_parquet(openaq_path)
    
    # Interpolar datos terrestres a la rejilla
    ground_pm25 = None
    ground_o3 = None
    
    for param in ["pm25", "o3"]:
        param_data = df_openaq[df_openaq["parameter"].str.lower() == param]
        if not param_data.empty:
            # Crear datos interpolados simple (promedio por zona)
            avg_value = param_data["value"].mean()
            param_array = xr.full_like(no2, avg_value, dtype=float)
            if param == "pm25":
                ground_pm25 = param_array
            elif param == "o3":
                ground_o3 = param_array
            print(f"   ✅ {param.upper()}: {len(param_data)} estaciones, promedio={avg_value:.2f}")
    
    # 4. Normalizar variables
    print("4️⃣ Normalizando variables...")
    
    def minmax_normalize(data):
        return (data - data.min()) / (data.max() - data.min() + 1e-9)
    
    no2_norm = minmax_normalize(no2)
    temp_norm = minmax_normalize(temp)
    wind_norm = (wind_speed < 2.0).astype(float)  # Penalizar viento bajo
    
    pm25_norm = minmax_normalize(ground_pm25) if ground_pm25 is not None else xr.zeros_like(no2)
    o3_norm = minmax_normalize(ground_o3) if ground_o3 is not None else xr.zeros_like(no2)
    
    print("   ✅ Variables normalizadas")
    
    # 5. Calcular índice de riesgo
    print("5️⃣ Calculando AIR Risk Score...")
    
    risk_score = (
        0.30 * no2_norm +           # NO₂ (30%)
        0.25 * o3_norm +            # O₃ (25%)
        0.20 * pm25_norm +          # PM2.5 (20%)
        0.15 * temp_norm +          # Temperatura (15%)
        0.10 * wind_norm            # Viento bajo (10%)
    ) * 100
    
    print(f"   ✅ Risk Score: [{float(risk_score.min()):.1f}, {float(risk_score.max()):.1f}]")
    
    # 6. Clasificar riesgo
    print("6️⃣ Clasificando riesgo...")
    
    # Usar numpy para evitar problemas con xarray.where
    risk_values = risk_score.values
    risk_class_values = np.where(risk_values < 34, "good",
                                np.where(risk_values <= 66, "moderate", "bad"))
    
    risk_class = xr.DataArray(
        risk_class_values,
        dims=risk_score.dims,
        coords=risk_score.coords
    )
    
    unique_classes, counts = np.unique(risk_class_values, return_counts=True)
    for cls, count in zip(unique_classes, counts):
        print(f"   • {cls}: {count} puntos")
    
    # 7. Crear dataset final
    print("7️⃣ Creando dataset final...")
    
    final_dataset = xr.Dataset({
        'no2': no2,
        'temp': temp,
        'wind': wind_speed,
        'risk_score': risk_score,
        'risk_class': risk_class
    })
    
    # Agregar datos terrestres si están disponibles
    if ground_pm25 is not None:
        final_dataset['pm25'] = ground_pm25
    if ground_o3 is not None:
        final_dataset['o3'] = ground_o3
    
    # Agregar metadatos
    final_dataset.attrs.update({
        "title": "CleanSky Los Angeles - AIR Risk Score Dataset",
        "description": "Unified atmospheric risk assessment combining satellite and ground-based observations",
        "created": datetime.now().isoformat(),
        "phase": "2",
        "spatial_resolution": "demo grid",
        "risk_calculation": "Weighted combination of NO₂, O₃, PM2.5, temperature, and wind dispersion factors"
    })
    
    print(f"   ✅ Dataset final: {dict(final_dataset.dims)}")
    print(f"   • Variables: {list(final_dataset.data_vars.keys())}")
    
    # 8. Guardar (usando NetCDF en lugar de Zarr)
    print("8️⃣ Guardando resultado...")
    
    output_nc = os.path.join(data_out, "airs_risk.nc")
    final_dataset.to_netcdf(output_nc)
    
    # También crear versión zarr alternativa (solo estructura)
    output_zarr_alt = os.path.join(data_out, "airs_risk_alt.zarr")
    if os.path.exists(output_zarr_alt):
        import shutil
        shutil.rmtree(output_zarr_alt)
    
    # Intentar guardar zarr con configuración simple
    try:
        final_dataset.to_zarr(output_zarr_alt, mode="w")
        print(f"   ✅ Guardado como NetCDF: {output_nc}")
        print(f"   ✅ Guardado como Zarr: {output_zarr_alt}")
    except Exception as e:
        print(f"   ⚠️  Zarr falló ({e}), solo NetCDF: {output_nc}")
    
    # 9. Validación final
    print("9️⃣ Validación final...")
    
    file_size_nc = os.path.getsize(output_nc) / 1024
    print(f"   • Archivo NetCDF: {file_size_nc:.1f} KB")
    
    # Verificar recarga
    ds_test = xr.open_dataset(output_nc)
    print(f"   • Recarga exitosa: {dict(ds_test.dims)}")
    
    # Estadísticas finales
    if "risk_score" in ds_test.data_vars:
        risk_mean = float(ds_test.risk_score.mean())
        risk_std = float(ds_test.risk_score.std())
        print(f"   • Risk Score: μ={risk_mean:.1f}, σ={risk_std:.1f}")
    
    ds_test.close()
    
    print("\n🎉 FASE 2 COMPLETADA EXITOSAMENTE!")
    print("=" * 50)
    print("📊 RESUMEN FINAL:")
    print(f"   • Dataset guardado: {output_nc}")
    print(f"   • Dimensiones: {dict(final_dataset.dims)}")
    print(f"   • Variables: {len(final_dataset.data_vars)}")
    print(f"   • Risk Score rango: [{float(risk_score.min()):.1f}, {float(risk_score.max()):.1f}]")
    print(f"   • Clasificaciones: {list(unique_classes)}")
    
    return final_dataset

if __name__ == "__main__":
    try:
        dataset = simple_risk_calculation()
        print("\n✅ Listo para análisis y visualización!")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()