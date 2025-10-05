"""
Descarga lluvia (IMERG) y viento/temperatura (MERRA-2) para correlación meteorológica.
"""
import earthaccess
import xarray as xr
from typing import Tuple, Optional, List
try:
    from .utils import (
        BBOX_LA, DATA_DIR, IMERG_CONFIG, MERRA2_CONFIG,
        ensure_data_dirs, get_recent_date_range, validate_bbox,
        log_info, log_error, log_success
    )
except ImportError:
    from utils import (
        BBOX_LA, DATA_DIR, IMERG_CONFIG, MERRA2_CONFIG,
        ensure_data_dirs, get_recent_date_range, validate_bbox,
        log_info, log_error, log_success
    )

def authenticate_earthdata() -> bool:
    """Autenticar con NASA EarthData."""
    try:
        earthaccess.login()
        log_success("Autenticado con NASA EarthData (meteorología)")
        return True
    except Exception as e:
        log_error(f"Error de autenticación EarthData: {e}")
        return False

def fetch_imerg_precip(
    bbox: Tuple[float, float, float, float] = BBOX_LA,
    start: Optional[str] = None,
    end: Optional[str] = None
) -> Optional[str]:
    """
    Descargar datos de precipitación IMERG.
    
    Args:
        bbox: Bounding box (west, south, east, north)
        start: Fecha inicio YYYY-MM-DD
        end: Fecha fin YYYY-MM-DD
        
    Returns:
        Path del archivo Zarr creado o None si falla
    """
    ensure_data_dirs()
    
    if not validate_bbox(bbox):
        log_error("Bounding box inválido para IMERG")
        return None
    
    if not start or not end:
        start, end = get_recent_date_range(days_back=1)
    
    log_info(f"Descargando IMERG precipitación para {start} - {end}")
    
    if not authenticate_earthdata():
        return None
    
    try:
        # Buscar datos IMERG
        results = earthaccess.search_data(
            short_name=IMERG_CONFIG["short_name"],
            temporal=(start, end),
            bounding_box=bbox
        )
        
        if not results:
            log_error("No se encontraron archivos IMERG")
            return None
        
        log_info(f"Encontrados {len(results)} archivos IMERG")
        
        # Abrir primer dataset
        files = earthaccess.open(results[0:1])
        ds = xr.open_dataset(files[0])
        
        # Recortar a bounding box
        west, south, east, north = bbox
        ds_cropped = ds.sel(
            lon=slice(west, east),
            lat=slice(south, north)
        )
        
        # Extraer precipitación
        var_name = IMERG_CONFIG["variable_name"]
        if var_name not in ds_cropped:
            # Nombres alternativos para precipitación
            possible_names = [
                "precipitationCal",
                "precipitation", 
                "precip",
                "HQprecipitation"
            ]
            
            found_var = None
            for name in possible_names:
                if name in ds_cropped:
                    found_var = name
                    break
            
            if not found_var:
                log_error(f"Variable precipitación no encontrada. Variables: {list(ds_cropped.variables)}")
                return None
            
            var_name = found_var
        
        precip_data = ds_cropped[var_name]
        
        # Crear dataset con metadatos
        output_ds = precip_data.to_dataset(name=IMERG_CONFIG["output_name"])
        output_ds.attrs.update({
            "title": "IMERG Precipitation Data",
            "source": "NASA GPM IMERG",
            "bbox": bbox,
            "temporal_range": f"{start} to {end}",
            "processing_date": str(xr.core.utils.datetime.datetime.now()),
            "units": getattr(precip_data, "units", "mm/hr")
        })
        
        # Guardar como Zarr
        output_path = DATA_DIR / IMERG_CONFIG["zarr_path"]
        output_ds.to_zarr(output_path, mode="w")
        
        log_success(f"IMERG precipitación guardado en {output_path}")
        return str(output_path)
        
    except Exception as e:
        log_error(f"Error descargando IMERG: {e}")
        return None
    
    finally:
        try:
            if 'ds' in locals():
                ds.close()
        except:
            pass

def fetch_merra2_wind_temp(
    bbox: Tuple[float, float, float, float] = BBOX_LA,
    start: Optional[str] = None,
    end: Optional[str] = None
) -> Optional[str]:
    """
    Descargar temperatura y viento de MERRA-2.
    
    Args:
        bbox: Bounding box (west, south, east, north) 
        start: Fecha inicio YYYY-MM-DD
        end: Fecha fin YYYY-MM-DD
        
    Returns:
        Path del archivo Zarr creado o None si falla
    """
    ensure_data_dirs()
    
    if not validate_bbox(bbox):
        log_error("Bounding box inválido para MERRA-2")
        return None
    
    if not start or not end:
        start, end = get_recent_date_range(days_back=1)
    
    log_info(f"Descargando MERRA-2 temperatura/viento para {start} - {end}")
    
    if not authenticate_earthdata():
        return None
    
    try:
        # Buscar datos MERRA-2
        results = earthaccess.search_data(
            short_name=MERRA2_CONFIG["short_name"],
            temporal=(start, end),
            bounding_box=bbox
        )
        
        if not results:
            log_error("No se encontraron archivos MERRA-2")
            return None
        
        log_info(f"Encontrados {len(results)} archivos MERRA-2")
        
        # Abrir primer dataset
        files = earthaccess.open(results[0:1])
        ds = xr.open_dataset(files[0])
        
        # Recortar a bounding box
        west, south, east, north = bbox
        ds_cropped = ds.sel(
            lon=slice(west, east),
            lat=slice(south, north)
        )
        
        # Extraer variables meteorológicas
        target_vars = MERRA2_CONFIG["variables"]
        available_vars = []
        
        for var in target_vars:
            if var in ds_cropped:
                available_vars.append(var)
            else:
                log_info(f"Variable {var} no encontrada en MERRA-2")
        
        if not available_vars:
            log_error(f"Ninguna variable meteorológica encontrada. Variables disponibles: {list(ds_cropped.variables)}")
            return None
        
        # Seleccionar variables disponibles
        met_data = ds_cropped[available_vars]
        
        # Agregar metadatos
        met_data.attrs.update({
            "title": "MERRA-2 Meteorological Data",
            "source": "NASA MERRA-2",
            "variables": available_vars,
            "bbox": bbox,
            "temporal_range": f"{start} to {end}",
            "processing_date": str(xr.core.utils.datetime.datetime.now())
        })
        
        # Guardar como Zarr
        output_path = DATA_DIR / MERRA2_CONFIG["zarr_path"]
        met_data.to_zarr(output_path, mode="w")
        
        log_success(f"MERRA-2 guardado en {output_path}")
        log_info(f"Variables guardadas: {available_vars}")
        
        return str(output_path)
        
    except Exception as e:
        log_error(f"Error descargando MERRA-2: {e}")
        return None
    
    finally:
        try:
            if 'ds' in locals():
                ds.close()
        except:
            pass

def validate_meteorology_data(zarr_path: str, data_type: str) -> bool:
    """Validar datos meteorológicos."""
    try:
        ds = xr.open_zarr(zarr_path)
        
        if data_type == "imerg":
            expected_var = IMERG_CONFIG["output_name"]
            if expected_var not in ds:
                log_error(f"Variable {expected_var} no encontrada en IMERG")
                return False
        
        elif data_type == "merra2":
            available_vars = list(ds.data_vars)
            if not available_vars:
                log_error("No hay variables meteorológicas en MERRA-2")
                return False
        
        log_success(f"Validación {data_type} exitosa: {dict(ds.dims)}")
        return True
        
    except Exception as e:
        log_error(f"Error validando {data_type}: {e}")
        return False

if __name__ == "__main__":
    # Test standalone
    log_info("Probando descarga de datos meteorológicos...")
    
    imerg_result = fetch_imerg_precip()
    if imerg_result:
        validate_meteorology_data(imerg_result, "imerg")
    
    merra2_result = fetch_merra2_wind_temp()
    if merra2_result:
        validate_meteorology_data(merra2_result, "merra2")