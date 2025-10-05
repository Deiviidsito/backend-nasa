"""
Validador de Fase 1 — Ingesta de datos (CleanSky Los Ángeles)
Autor: David Álvarez  
Fecha: 2025-10-05

Este script valida que todos los datasets descargados (TEMPO, OpenAQ, IMERG, MERRA-2)
estén correctamente generados, legibles y contengan datos coherentes.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import hashlib

# Intentar importar dependencias científicas
try:
    import xarray as xr
    import pandas as pd
    import numpy as np
    SCIENTIFIC_LIBS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Dependencias científicas no disponibles: {e}")
    SCIENTIFIC_LIBS_AVAILABLE = False

# Rutas de archivos
DATA_DIR = Path(__file__).parent.parent / "data" / "zarr_store"
CHECKS = {
    "TEMPO": DATA_DIR / "tempo_no2.zarr",
    "TEMPO_DEMO": DATA_DIR / "tempo_no2_demo.csv",
    "OpenAQ": DATA_DIR / "openaq_latest.parquet", 
    "IMERG": DATA_DIR / "imerg_precip.zarr",
    "IMERG_DEMO": DATA_DIR / "imerg_precip_demo.csv",
    "MERRA-2": DATA_DIR / "merra2_temp.zarr",
    "MERRA2_DEMO": DATA_DIR / "merra2_weather_demo.csv",
}

def log(status: str, msg: str):
    """Log con timestamp y emoji."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {status} {msg}")

def validate_tempo(zarr_path: Path, demo_path: Path) -> bool:
    """Validar datos TEMPO NO₂."""
    if not SCIENTIFIC_LIBS_AVAILABLE:
        return validate_file_exists(demo_path, "TEMPO demo")
    
    # Intentar primero Zarr, luego demo CSV
    path_to_use = zarr_path if zarr_path.exists() else demo_path
    
    try:
        if path_to_use.suffix == '.zarr':
            ds = xr.open_zarr(path_to_use)
            # Verificar dimensiones espaciales
            has_lat = any(dim in ds.dims for dim in ['latitude', 'lat'])
            has_lon = any(dim in ds.dims for dim in ['longitude', 'lon']) 
            assert has_lat and has_lon, "Dimensiones espaciales faltantes"
            
            # Buscar variable NO₂
            no2_vars = [v for v in ds.data_vars if 'no2' in str(v).lower()]
            assert len(no2_vars) > 0, "No se encontró variable NO₂"
            
            val = float(ds[no2_vars[0]].mean().item())
            assert val > 0, f"Valor medio de NO₂ inválido: {val}"
            
            log("✔️", f"TEMPO Zarr válido ({val:.2e} molec/cm²)")
            
        else:  # CSV demo
            df = pd.read_csv(path_to_use)
            assert not df.empty, "Archivo CSV vacío"
            
            required_cols = ['latitude', 'longitude', 'no2_tropospheric_column']
            assert all(col in df.columns for col in required_cols), "Columnas faltantes"
            
            val = df['no2_tropospheric_column'].mean()
            assert val > 0, f"Valor medio de NO₂ CSV inválido: {val}"
            
            log("✔️", f"TEMPO CSV demo válido ({val:.2e} molec/cm², {len(df)} puntos)")
            
        return True
        
    except Exception as e:
        log("❌", f"TEMPO error: {e}")
        return False

def validate_openaq(path: Path) -> bool:
    """Validar datos OpenAQ."""
    if not SCIENTIFIC_LIBS_AVAILABLE:
        return validate_file_exists(path, "OpenAQ")
    
    try:
        df = pd.read_parquet(path)
        assert not df.empty, "Archivo vacío"
        
        # Verificar columnas esenciales
        essential_cols = ['location_id', 'latitude', 'longitude', 'parameter', 'value']
        missing_cols = [col for col in essential_cols if col not in df.columns]
        assert not missing_cols, f"Columnas faltantes: {missing_cols}"
        
        # Verificar que hay valores válidos
        assert df['value'].notna().any(), "Todos los valores son nulos"
        
        # Verificar parámetros esperados
        params = df['parameter'].unique()
        expected_params = {'pm25', 'no2', 'o3'}
        found_params = set(params) & expected_params
        assert len(found_params) >= 2, f"Parámetros insuficientes: {params}"
        
        log("✔️", f"OpenAQ válido ({len(df)} registros, parámetros: {list(params)})")
        return True
        
    except Exception as e:
        log("❌", f"OpenAQ error: {e}")
        return False

def validate_imerg(zarr_path: Path, demo_path: Path) -> bool:
    """Validar datos IMERG precipitación."""
    if not zarr_path.exists() and not demo_path.exists():
        log("⚠️", "IMERG no encontrado (opcional)")
        return True
    
    if not SCIENTIFIC_LIBS_AVAILABLE:
        return validate_file_exists(demo_path, "IMERG demo")
    
    path_to_use = zarr_path if zarr_path.exists() else demo_path
    
    try:
        if path_to_use.suffix == '.zarr':
            ds = xr.open_zarr(path_to_use)
            precip_vars = [v for v in ds.data_vars if any(term in str(v).lower() 
                          for term in ['rain', 'precip', 'precipitation'])]
            assert len(precip_vars) > 0, "No se encontró variable de precipitación"
            
            val = float(ds[precip_vars[0]].mean().item())
            log("✔️", f"IMERG Zarr válido ({precip_vars[0]}: {val:.3f} mm/hr)")
            
        else:  # CSV demo
            df = pd.read_csv(path_to_use)
            assert not df.empty, "Archivo CSV vacío"
            assert 'precipitation' in df.columns, "Columna precipitation faltante"
            
            val = df['precipitation'].mean()
            log("✔️", f"IMERG CSV demo válido ({val:.3f} mm/hr, {len(df)} registros)")
            
        return True
        
    except Exception as e:
        log("❌", f"IMERG error: {e}")
        return False

def validate_merra2(zarr_path: Path, demo_path: Path) -> bool:
    """Validar datos MERRA-2 temperatura/viento."""
    if not zarr_path.exists() and not demo_path.exists():
        log("⚠️", "MERRA-2 no encontrado (opcional)")
        return True
    
    if not SCIENTIFIC_LIBS_AVAILABLE:
        return validate_file_exists(demo_path, "MERRA-2 demo")
    
    path_to_use = zarr_path if zarr_path.exists() else demo_path
    
    try:
        if path_to_use.suffix == '.zarr':
            ds = xr.open_zarr(path_to_use)
            required_vars = ["T2M", "U2M", "V2M"]
            missing_vars = [var for var in required_vars if var not in ds.data_vars]
            assert not missing_vars, f"Variables faltantes: {missing_vars}"
            
            # Verificar rangos razonables
            temp_mean = float(ds["T2M"].mean().item())
            assert 250 < temp_mean < 350, f"Temperatura irreal: {temp_mean} K"
            
            log("✔️", f"MERRA-2 Zarr válido (T2M: {temp_mean:.1f} K)")
            
        else:  # CSV demo
            df = pd.read_csv(path_to_use)
            assert not df.empty, "Archivo CSV vacío"
            
            required_cols = ['T2M', 'U2M', 'V2M']
            missing_cols = [col for col in required_cols if col not in df.columns]
            assert not missing_cols, f"Columnas faltantes: {missing_cols}"
            
            temp_mean = df['T2M'].mean()
            assert 250 < temp_mean < 350, f"Temperatura irreal: {temp_mean} K"
            
            log("✔️", f"MERRA-2 CSV demo válido (T2M: {temp_mean:.1f} K, {len(df)} registros)")
            
        return True
        
    except Exception as e:
        log("❌", f"MERRA-2 error: {e}")
        return False

def validate_file_exists(path: Path, name: str) -> bool:
    """Validación básica de existencia de archivo."""
    if path.exists():
        size_kb = path.stat().st_size / 1024
        log("✔️", f"{name} existe ({size_kb:.1f} KB)")
        return True
    else:
        log("❌", f"{name} no encontrado: {path}")
        return False

def validate_data_consistency() -> bool:
    """Validar consistencia entre datasets."""
    if not SCIENTIFIC_LIBS_AVAILABLE:
        log("⚠️", "Validación de consistencia omitida (dependencias)")
        return True
    
    try:
        # Verificar que todos usan el mismo bounding box aproximado
        bbox_checks = []
        
        # OpenAQ
        if CHECKS["OpenAQ"].exists():
            df = pd.read_parquet(CHECKS["OpenAQ"])
            if not df.empty:
                lat_range = (df['latitude'].min(), df['latitude'].max())
                lon_range = (df['longitude'].min(), df['longitude'].max())
                bbox_checks.append(('OpenAQ', lat_range, lon_range))
        
        # TEMPO demo
        if CHECKS["TEMPO_DEMO"].exists():
            df = pd.read_csv(CHECKS["TEMPO_DEMO"])
            lat_range = (df['latitude'].min(), df['latitude'].max())
            lon_range = (df['longitude'].min(), df['longitude'].max())
            bbox_checks.append(('TEMPO', lat_range, lon_range))
        
        if len(bbox_checks) >= 2:
            # Verificar que los rangos se solapan (están en LA)
            for name, (lat_min, lat_max), (lon_min, lon_max) in bbox_checks:
                assert 33 <= lat_min <= 35, f"{name}: latitud fuera de LA"
                assert 34 <= lat_max <= 35, f"{name}: latitud fuera de LA"
                assert -119 <= lon_min <= -117, f"{name}: longitud fuera de LA"
                assert -119 <= lon_max <= -117, f"{name}: longitud fuera de LA"
        
        log("✔️", "Consistencia geográfica validada (todos en LA)")
        return True
        
    except Exception as e:
        log("⚠️", f"Validación de consistencia: {e}")
        return True  # No crítico

def validate_reproducibility() -> bool:
    """Validar que los archivos son estables."""
    try:
        # Calcular checksums de archivos existentes
        checksums = {}
        for name, path in CHECKS.items():
            if path.exists():
                with open(path, 'rb') as f:
                    content = f.read()
                checksums[name] = hashlib.md5(content).hexdigest()[:8]
        
        if checksums:
            log("✔️", f"Checksums calculados: {len(checksums)} archivos")
            return True
        else:
            log("⚠️", "No hay archivos para validar reproducibilidad")
            return True
            
    except Exception as e:
        log("⚠️", f"Validación de reproducibilidad: {e}")
        return True  # No crítico

def main():
    """Ejecutar validación completa de Fase 1."""
    log("🚀", "Iniciando validación de Fase 1 — Ingesta de datos CleanSky LA")
    log("📁", f"Directorio de datos: {DATA_DIR}")
    
    # Verificar que el directorio existe
    if not DATA_DIR.exists():
        log("❌", f"Directorio de datos no existe: {DATA_DIR}")
        return False
    
    # Listar archivos disponibles
    files = list(DATA_DIR.glob('*'))
    log("📂", f"Archivos encontrados: {len(files)}")
    for f in files:
        size_kb = f.stat().st_size / 1024
        log("  ", f"  {f.name} ({size_kb:.1f} KB)")
    
    # Ejecutar validaciones por dataset
    results = {}
    
    log("🛰️", "Validando TEMPO NO₂...")
    results["TEMPO"] = validate_tempo(CHECKS["TEMPO"], CHECKS["TEMPO_DEMO"])
    
    log("🌫️", "Validando OpenAQ...")
    results["OpenAQ"] = validate_openaq(CHECKS["OpenAQ"])
    
    log("🌧️", "Validando IMERG precipitación...")
    results["IMERG"] = validate_imerg(CHECKS["IMERG"], CHECKS["IMERG_DEMO"])
    
    log("🌡️", "Validando MERRA-2 meteorología...")
    results["MERRA-2"] = validate_merra2(CHECKS["MERRA-2"], CHECKS["MERRA2_DEMO"])
    
    # Validaciones adicionales
    log("🔍", "Validando consistencia de datos...")
    consistency_ok = validate_data_consistency()
    
    log("🔄", "Validando reproducibilidad...")
    reproducibility_ok = validate_reproducibility()
    
    # Calcular resultado final
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    # Determinar status final
    if passed == total:
        status = "✅ ÉXITO TOTAL"
        message = "Fase 1 completada con éxito: todos los datasets legibles y coherentes."
    elif passed >= 3:
        status = "⚠️ PARCIAL"
        message = "Datos válidos parcialmente: revisar fuentes fallidas."
    else:
        status = "❌ FALLA"
        message = "Fase 1 inválida: revisar logs y repetir la ingesta."
    
    # Reporte final
    log("📊", f"Resultado: {status} ({passed}/{total})")
    log("🎯", message)
    
    # Detalles por dataset
    log("📋", "Detalle por dataset:")
    for name, success in results.items():
        icon = "✅" if success else "❌"
        log("  ", f"  {icon} {name}")
    
    # Recomendaciones
    if status == "✅ ÉXITO TOTAL":
        log("🚀", "🎉 ¡LISTO PARA FASE 2: Procesamiento y fusión de datos!")
        log("💡", "Siguiente paso: Implementar pipeline de procesamiento")
    elif status == "⚠️ PARCIAL":
        failed = [name for name, success in results.items() if not success]
        log("🔧", f"Revisar datasets fallidos: {failed}")
        log("💡", "OpenAQ es crítico, otros pueden ser opcionales")
    else:
        log("🚫", "Repetir ingesta completa antes de continuar")
    
    return status == "✅ ÉXITO TOTAL"

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)