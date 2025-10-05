#!/usr/bin/env python3
"""
Versión ultra-simple para debug
"""

import pandas as pd
import numpy as np
import os

def ultra_simple():
    print("🔍 Debug ultra-simple")
    
    # 1. Solo TEMPO
    print("1. Cargando TEMPO...")
    df_tempo = pd.read_csv("../data/zarr_store/tempo_no2_demo.csv")
    print(f"   ✅ {len(df_tempo)} registros")
    
    # 2. Crear riesgo básico solo con pandas
    print("2. Calculando riesgo...")
    no2_values = df_tempo['no2_tropospheric_column'].values
    no2_norm = (no2_values - no2_values.min()) / (no2_values.max() - no2_values.min())
    risk_score = no2_norm * 100
    
    risk_class = np.where(risk_score < 34, "good",
                         np.where(risk_score <= 66, "moderate", "bad"))
    
    print(f"   ✅ Risk Score: [{risk_score.min():.1f}, {risk_score.max():.1f}]")
    
    # 3. Crear DataFrame de salida
    print("3. Creando resultado...")
    result_df = df_tempo.copy()
    result_df['risk_score'] = risk_score
    result_df['risk_class'] = risk_class
    
    # 4. Guardar CSV simple
    print("4. Guardando...")
    os.makedirs("../data/processed", exist_ok=True)
    result_df.to_csv("../data/processed/airs_risk_simple.csv", index=False)
    
    print("✅ ¡LISTO!")
    print(f"   • {len(result_df)} puntos procesados")
    print(f"   • Archivo: ../data/processed/airs_risk_simple.csv")
    
    # Estadísticas
    unique_classes, counts = np.unique(risk_class, return_counts=True)
    for cls, count in zip(unique_classes, counts):
        print(f"   • {cls}: {count} puntos")

if __name__ == "__main__":
    ultra_simple()