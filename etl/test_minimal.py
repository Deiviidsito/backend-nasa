#!/usr/bin/env python3
"""
Prueba mínima para identificar el problema
"""

import pandas as pd
import xarray as xr
import numpy as np
import os

def simple_test():
    print("🧪 Prueba mínima")
    
    # 1. Cargar datos CSV
    data_path = "../data/zarr_store/tempo_no2_demo.csv"
    if not os.path.exists(data_path):
        print("❌ Archivo no encontrado")
        return False
    
    print("📂 Cargando CSV...")
    df = pd.read_csv(data_path)
    print(f"   ✅ {len(df)} registros cargados")
    
    # 2. Convertir a xarray
    print("🔄 Convirtiendo a xarray...")
    ds = df.set_index(['latitude', 'longitude']).to_xarray()
    ds = ds.rename({'latitude': 'lat', 'longitude': 'lon'})
    print(f"   ✅ Dataset: {dict(ds.dims)}")
    
    # 3. Extraer NO2
    print("🔍 Extrayendo NO2...")
    no2 = ds['no2_tropospheric_column']
    print(f"   ✅ NO2: {no2.dims}, rango [{float(no2.min()):.2e}, {float(no2.max()):.2e}]")
    
    # 4. Normalizar (función simple)
    print("📊 Normalizando...")
    no2_norm = (no2 - no2.min()) / (no2.max() - no2.min())
    print(f"   ✅ Normalizado: [{float(no2_norm.min()):.2f}, {float(no2_norm.max()):.2f}]")
    
    # 5. Calcular riesgo simple
    print("🧮 Calculando riesgo...")
    risk_score = no2_norm * 100  # Riesgo básico basado solo en NO2
    print(f"   ✅ Risk Score: [{float(risk_score.min()):.1f}, {float(risk_score.max()):.1f}]")
    
    # 6. Clasificar
    print("🚦 Clasificando...")
    risk_class = xr.where(risk_score < 34, "good",
                         xr.where(risk_score <= 66, "moderate", "bad"))
    print(f"   ✅ Clases: {np.unique(risk_class.values)}")
    
    # 7. Crear dataset final
    print("💾 Creando dataset final...")
    final_ds = xr.Dataset({
        'no2': no2,
        'risk_score': risk_score,
        'risk_class': risk_class
    })
    print(f"   ✅ Dataset final: {dict(final_ds.dims)}")
    
    # 8. Guardar
    output_path = "../data/processed/airs_risk.zarr"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print("💾 Guardando...")
    if os.path.exists(output_path):
        import shutil
        shutil.rmtree(output_path)
    
    final_ds.to_zarr(output_path, mode="w")
    print(f"   ✅ Guardado en {output_path}")
    
    print("🎉 ¡PRUEBA EXITOSA!")
    return True

if __name__ == "__main__":
    try:
        simple_test()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()