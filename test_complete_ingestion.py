"""
Script mejorado para probar la ingesta completa con datos simulados cuando sea necesario.
"""
import numpy as np
import xarray as xr
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime, timedelta

# Agregar el directorio padre al path
sys.path.append(str(Path(__file__).parent))

from etl.utils import DATA_DIR, BBOX_LA, ensure_data_dirs, log_info, log_success, log_error

def create_mock_tempo_data() -> str:
    """Crear datos simulados de TEMPO NO₂ para pruebas."""
    ensure_data_dirs()
    
    log_info("🛰️ Creando datos simulados TEMPO NO₂...")
    
    # Bounding box LA
    west, south, east, north = BBOX_LA
    
    # Crear grilla
    lons = np.linspace(west, east, 50)
    lats = np.linspace(south, north, 30)
    time = pd.date_range('2025-10-05', periods=1, freq='H')
    
    # Simular valores NO₂ (columna troposférica en molec/cm²)
    np.random.seed(42)  # Para reproducibilidad
    no2_values = np.random.uniform(1e15, 5e15, (len(time), len(lats), len(lons)))
    
    # Crear dataset
    ds = xr.Dataset({
        'no2_tropospheric_column': (['time', 'latitude', 'longitude'], no2_values)
    }, coords={
        'longitude': lons,
        'latitude': lats,
        'time': time
    })
    
    # Agregar atributos
    ds.attrs.update({
        'title': 'TEMPO NO2 Simulated Data',
        'source': 'Mock data for testing',
        'bbox': BBOX_LA,
        'created': str(datetime.now())
    })
    
    output_path = DATA_DIR / "tempo_no2.zarr"
    ds.to_zarr(output_path, mode='w')
    
    log_success(f"✅ TEMPO simulado guardado: {output_path}")
    return str(output_path)

def create_mock_imerg_data() -> str:
    """Crear datos simulados de IMERG precipitación."""
    ensure_data_dirs()
    
    log_info("🌧️ Creando datos simulados IMERG precipitación...")
    
    west, south, east, north = BBOX_LA
    
    # Crear grilla más fina para precipitación
    lons = np.linspace(west, east, 40)
    lats = np.linspace(south, north, 25)
    time = pd.date_range('2025-10-05', periods=24, freq='H')
    
    # Simular precipitación (mm/hr)
    np.random.seed(123)
    precip_values = np.random.exponential(0.5, (len(time), len(lats), len(lons)))
    precip_values[precip_values > 10] = 0  # La mayoría del tiempo no llueve
    
    # Crear dataset
    ds = xr.Dataset({
        'precipitation': (['time', 'lat', 'lon'], precip_values)
    }, coords={
        'lon': lons,
        'lat': lats,
        'time': time
    })
    
    ds.attrs.update({
        'title': 'IMERG Precipitation Simulated Data',
        'source': 'Mock data for testing',
        'units': 'mm/hr'
    })
    
    output_path = DATA_DIR / "imerg_precip.zarr"
    ds.to_zarr(output_path, mode='w')
    
    log_success(f"✅ IMERG simulado guardado: {output_path}")
    return str(output_path)

def create_mock_merra2_data() -> str:
    """Crear datos simulados de MERRA-2 temperatura y viento."""
    ensure_data_dirs()
    
    log_info("🌡️ Creando datos simulados MERRA-2 temperatura/viento...")
    
    west, south, east, north = BBOX_LA
    
    lons = np.linspace(west, east, 35)
    lats = np.linspace(south, north, 20)
    time = pd.date_range('2025-10-05', periods=24, freq='H')
    
    # Simular datos meteorológicos
    np.random.seed(456)
    temp_values = np.random.normal(20, 5, (len(time), len(lats), len(lons))) + 273.15  # Kelvin
    u_wind = np.random.normal(2, 3, (len(time), len(lats), len(lons)))  # m/s
    v_wind = np.random.normal(1, 2, (len(time), len(lats), len(lons)))  # m/s
    
    # Crear dataset
    ds = xr.Dataset({
        'T2M': (['time', 'lat', 'lon'], temp_values),
        'U2M': (['time', 'lat', 'lon'], u_wind),
        'V2M': (['time', 'lat', 'lon'], v_wind)
    }, coords={
        'lon': lons,
        'lat': lats,
        'time': time
    })
    
    ds.attrs.update({
        'title': 'MERRA-2 Temperature/Wind Simulated Data',
        'source': 'Mock data for testing'
    })
    
    output_path = DATA_DIR / "merra2_temp.zarr"
    ds.to_zarr(output_path, mode='w')
    
    log_success(f"✅ MERRA-2 simulado guardado: {output_path}")
    return str(output_path)

def run_complete_ingestion_with_mocks():
    """Ejecutar ingesta completa usando datos simulados cuando sea necesario."""
    log_info("🚀 Iniciando ingesta CleanSky Los Ángeles con datos simulados...")
    
    results = {}
    
    # 1. TEMPO (simulado)
    try:
        tempo_path = create_mock_tempo_data()
        results['tempo'] = tempo_path
    except Exception as e:
        log_error(f"Error TEMPO simulado: {e}")
        results['tempo'] = None
    
    # 2. OpenAQ (real - ya funciona)
    try:
        from etl.ingest_openaq import fetch_latest_openaq
        log_info("🌫️ Ejecutando OpenAQ real...")
        openaq_path = fetch_latest_openaq()
        results['openaq'] = openaq_path
    except Exception as e:
        log_error(f"Error OpenAQ: {e}")
        results['openaq'] = None
    
    # 3. IMERG (simulado)
    try:
        imerg_path = create_mock_imerg_data()
        results['imerg'] = imerg_path
    except Exception as e:
        log_error(f"Error IMERG simulado: {e}")
        results['imerg'] = None
    
    # 4. MERRA-2 (simulado)
    try:
        merra2_path = create_mock_merra2_data()
        results['merra2'] = merra2_path
    except Exception as e:
        log_error(f"Error MERRA-2 simulado: {e}")
        results['merra2'] = None
    
    # Resumen final
    successful = sum(1 for r in results.values() if r)
    total = len(results)
    
    log_info(f"\n📊 RESUMEN FINAL:")
    for name, path in results.items():
        if path and Path(path).exists():
            size = Path(path).stat().st_size / (1024*1024)
            log_success(f"✅ {name.upper()}: {Path(path).name} ({size:.1f} MB)")
        else:
            log_error(f"❌ {name.upper()}: FALLO")
    
    if successful == total:
        log_success(f"🎉 ¡INGESTA COMPLETADA! {successful}/{total} datasets exitosos")
        return True
    else:
        log_error(f"⚠️ Ingesta parcial: {successful}/{total} datasets")
        return False

if __name__ == "__main__":
    success = run_complete_ingestion_with_mocks()
    sys.exit(0 if success else 1)