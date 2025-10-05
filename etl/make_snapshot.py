"""
Script maestro para ejecutar la Fase 2 completa y generar el dataset unificado con risk_score.
CleanSky Los Ángeles - NASA Space Apps Challenge 2024

Este script orquesta todo el proceso de fusión y cálculo del índice AIR Risk Score.
"""

import sys
import os
import traceback
from datetime import datetime
import xarray as xr

# Añadir el directorio actual al path para importar módulos locales
sys.path.insert(0, os.path.dirname(__file__))

from process_fusion import process_fusion

def print_banner():
    """Imprime banner de inicio de Fase 2."""
    print("=" * 80)
    print("🧩 CLEANSKY LOS ANGELES - FASE 2")
    print("   Procesamiento de riesgo atmosférico (AIR Risk Score)")
    print("=" * 80)
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def print_dataset_summary(ds: xr.Dataset):
    """
    Imprime un resumen detallado del dataset procesado.
    
    Args:
        ds: Dataset procesado
    """
    print("\n" + "=" * 60)
    print("📊 RESUMEN DEL DATASET PROCESADO")
    print("=" * 60)
    
    # Información básica
    print(f"Dimensiones: {dict(ds.dims)}")
    print(f"Coordenadas: {list(ds.coords.keys())}")
    print(f"Variables de datos: {len(ds.data_vars)}")
    print()
    
    # Variables principales
    print("🔍 Variables incluidas:")
    for var_name, var_data in ds.data_vars.items():
        try:
            min_val = float(var_data.min())
            max_val = float(var_data.max())
            mean_val = float(var_data.mean())
            
            units = var_data.attrs.get('units', 'sin unidad')
            
            print(f"   • {var_name:12s}: [{min_val:8.2f}, {max_val:8.2f}] μ={mean_val:8.2f} ({units})")
            
        except Exception as e:
            print(f"   • {var_name:12s}: Error calculando estadísticas: {e}")
    
    print()
    
    # Risk Score específico
    if "risk_score" in ds.data_vars:
        risk = ds.risk_score
        print("🎯 AIR Risk Score:")
        print(f"   • Rango: [{float(risk.min()):.1f}, {float(risk.max()):.1f}]")
        print(f"   • Promedio: {float(risk.mean()):.1f}")
        print(f"   • Desviación: {float(risk.std()):.1f}")
        print()
    
    # Risk Class específico
    if "risk_class" in ds.data_vars:
        risk_class = ds.risk_class
        print("🚦 Clasificación de riesgo:")
        
        # Contar valores únicos
        try:
            import numpy as np
            unique_classes, counts = np.unique(risk_class.values, return_counts=True)
            total_points = len(risk_class.values.flatten())
            
            for cls, count in zip(unique_classes, counts):
                percentage = (count / total_points) * 100
                print(f"   • {cls:10s}: {count:5d} puntos ({percentage:5.1f}%)")
        except Exception as e:
            print(f"   • Error contando clases: {e}")
        
        print()
    
    # Metadatos
    if ds.attrs:
        print("📋 Metadatos:")
        for key, value in ds.attrs.items():
            if isinstance(value, str) and len(value) > 60:
                value = value[:60] + "..."
            print(f"   • {key}: {value}")

def validate_requirements():
    """
    Valida que todos los requisitos estén disponibles.
    
    Returns:
        bool: True si todo está listo
    """
    print("🔍 Verificando requisitos...")
    
    # Verificar dependencias
    try:
        import xarray
        import numpy
        import pandas
        print("   ✅ Dependencias Python disponibles")
    except ImportError as e:
        print(f"   ❌ Dependencia faltante: {e}")
        return False
    
    # Verificar estructura de directorios
    base_dir = os.path.dirname(__file__)
    data_raw = os.path.join(base_dir, "../data/zarr_store")
    data_processed = os.path.join(base_dir, "../data/processed")
    
    if not os.path.exists(data_raw):
        print(f"   ❌ Directorio de datos crudos no encontrado: {data_raw}")
        return False
    else:
        print("   ✅ Directorio de datos crudos disponible")
    
    # Verificar archivos de entrada disponibles
    input_files = []
    for filename in os.listdir(data_raw):
        if filename.endswith(('.zarr', '.parquet', '.csv')):
            input_files.append(filename)
    
    if input_files:
        print(f"   ✅ Archivos de entrada encontrados: {len(input_files)}")
        for f in sorted(input_files[:5]):  # Mostrar primeros 5
            print(f"      • {f}")
        if len(input_files) > 5:
            print(f"      • ... y {len(input_files) - 5} más")
    else:
        print("   ⚠️  No se encontraron archivos de entrada")
        print("      Continuando con datos demo...")
    
    return True

def main():
    """Función principal que ejecuta toda la Fase 2."""
    
    print_banner()
    
    # Verificar requisitos
    if not validate_requirements():
        print("❌ Requisitos no cumplidos. Abortando.")
        return 1
    
    print()
    
    try:
        # Ejecutar procesamiento principal
        print("🚀 Iniciando procesamiento...")
        dataset = process_fusion()
        
        print("\n" + "🎉" * 20)
        print("✅ FASE 2 COMPLETADA CORRECTAMENTE")
        print("🎉" * 20)
        
        # Mostrar resumen
        print_dataset_summary(dataset)
        
        # Verificar archivo de salida
        output_path = os.path.join(os.path.dirname(__file__), "../data/processed/airs_risk.zarr")
        if os.path.exists(output_path):
            print("\n💾 Archivo de salida verificado:")
            print(f"   • Ubicación: {output_path}")
            
            # Calcular tamaño
            total_size = 0
            for dirpath, _, filenames in os.walk(output_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)
            
            size_mb = total_size / (1024 * 1024)
            print(f"   • Tamaño: {size_mb:.2f} MB")
            
            print(f"\n🎯 Dataset listo para análisis y visualización")
            print(f"   Puedes cargar el resultado con:")
            print(f"   >>> import xarray as xr")
            print(f"   >>> ds = xr.open_zarr('{output_path}')")
        
        print(f"\n⏰ Finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return 0
        
    except Exception as e:
        print("\n" + "❌" * 20)
        print("ERROR EN FASE 2")
        print("❌" * 20)
        print(f"Error: {str(e)}")
        print()
        print("Traceback completo:")
        traceback.print_exc()
        print()
        print("💡 Posibles soluciones:")
        print("   • Verificar que los datos de Fase 1 estén disponibles")
        print("   • Comprobar permisos de escritura en data/processed/")
        print("   • Revisar dependencias de Python")
        return 1

def test_quick():
    """
    Función de prueba rápida para verificar que el dataset se carga correctamente.
    """
    try:
        output_path = os.path.join(os.path.dirname(__file__), "../data/processed/airs_risk.zarr")
        
        if not os.path.exists(output_path):
            print("❌ Dataset no encontrado. Ejecutar make_snapshot.py primero.")
            return False
        
        print("🧪 Prueba rápida de consistencia...")
        ds = xr.open_zarr(output_path)
        
        # Verificaciones básicas
        assert "risk_score" in ds.data_vars, "Variable risk_score faltante"
        assert "risk_class" in ds.data_vars, "Variable risk_class faltante"
        
        risk_mean = float(ds.risk_score.mean())
        print(f"✅ Risk score promedio: {risk_mean:.1f}")
        
        # Contar clases
        try:
            import numpy as np
            unique_classes, counts = np.unique(ds.risk_class.values, return_counts=True)
            class_counts = dict(zip(unique_classes, counts))
            print(f"✅ Risk classes: {class_counts}")
        except:
            print("⚠️  No se pudieron contar las clases")
        
        print("✅ Prueba rápida exitosa")
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba rápida: {e}")
        return False

if __name__ == "__main__":
    # Verificar argumentos de línea de comandos
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        success = test_quick()
        sys.exit(0 if success else 1)
    else:
        result = main()
        sys.exit(result)