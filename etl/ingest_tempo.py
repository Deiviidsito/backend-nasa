"""
Descarga datos TEMPO NO₂ NRT desde EarthData (NASA).
"""
import earthaccess
import xarray as xr
import os
from typing import Tuple, Optional
try:
    from .utils import (
        BBOX_LA, DATA_DIR, TEMPO_CONFIG, 
        ensure_data_dirs, get_recent_date_range,
        log_info, log_error, log_success, validate_bbox
    )
except ImportError:
    from utils import (
        BBOX_LA, DATA_DIR, TEMPO_CONFIG, 
        ensure_data_dirs, get_recent_date_range,
        log_info, log_error, log_success, validate_bbox
    )

def authenticate_earthdata() -> bool:
    """Autenticar con NASA EarthData."""
    try:
        earthaccess.login()
        log_success("Autenticado con NASA EarthData")
        return True
    except Exception as e:
        log_error(f"Error de autenticación EarthData: {e}")
        return False

def fetch_tempo_no2(
    bbox: Tuple[float, float, float, float] = BBOX_LA,
    start: Optional[str] = None,
    end: Optional[str] = None
) -> Optional[str]:
    """
    Descargar datos TEMPO NO₂ y guardar en Zarr.
    
    Args:
        bbox: Bounding box (west, south, east, north)
        start: Fecha inicio YYYY-MM-DD (default: ayer)
        end: Fecha fin YYYY-MM-DD (default: hoy)
        
    Returns:
        Path del archivo Zarr creado o None si falla
    """
    ensure_data_dirs()
    
    if not validate_bbox(bbox):
        log_error("Bounding box inválido")
        return None
    
    if not start or not end:
        start, end = get_recent_date_range(days_back=2)
    
    log_info(f"Descargando TEMPO NO₂ para {start} - {end}, bbox: {bbox}")
    
    # Autenticar
    if not authenticate_earthdata():
        return None
    
    try:
        # Buscar datos TEMPO
        results = earthaccess.search_data(
            short_name=TEMPO_CONFIG["short_name"],
            temporal=(start, end),
            bounding_box=bbox
        )
        
        if not results:
            log_error("No se encontraron archivos TEMPO para el rango especificado")
            return None
        
        log_info(f"Encontrados {len(results)} archivos TEMPO")
        
        # Abrir primer dataset (streaming virtual)
        log_info("Abriendo dataset TEMPO...")
        files = earthaccess.open(results[0:1])  # Solo el primer archivo
        ds = xr.open_dataset(files[0])
        
        # Recortar a bounding box - detectar nombres de coordenadas
        west, south, east, north = bbox
        
        # Detectar nombres de coordenadas (pueden ser lon/longitude, lat/latitude)
        lon_name = None
        lat_name = None
        
        for coord in ds.coords:
            if coord.lower() in ['lon', 'longitude']:
                lon_name = coord
            elif coord.lower() in ['lat', 'latitude']: 
                lat_name = coord
        
        if not lon_name or not lat_name:
            log_error(f"Coordenadas no encontradas. Coordenadas disponibles: {list(ds.coords)}")
            return None
        
        log_info(f"Usando coordenadas: {lon_name}, {lat_name}")
        
        # Recortar usando los nombres correctos
        ds_cropped = ds.sel(
            {lon_name: slice(west, east), 
             lat_name: slice(south, north)}
        )
        
        # Extraer variable NO₂
        var_name = TEMPO_CONFIG["variable_name"]
        if var_name not in ds_cropped:
            # Intentar nombres alternativos
            possible_names = [
                "nitrogendioxide_tropospheric_column",
                "no2_tropospheric_column", 
                "NO2_column",
                "ColumnAmountNO2Trop"
            ]
            
            found_var = None
            for name in possible_names:
                if name in ds_cropped:
                    found_var = name
                    break
            
            if not found_var:
                log_error(f"Variable NO₂ no encontrada. Variables disponibles: {list(ds_cropped.variables)}")
                return None
            
            var_name = found_var
        
        no2_data = ds_cropped[var_name]
        
        # Crear dataset con metadatos
        output_ds = no2_data.to_dataset(name=TEMPO_CONFIG["output_name"])
        
        # Agregar metadatos
        output_ds.attrs.update({
            "title": "TEMPO NO2 Tropospheric Column",
            "source": "NASA TEMPO",
            "bbox": bbox,
            "temporal_range": f"{start} to {end}",
            "processing_date": str(xr.core.utils.datetime.datetime.now()),
            "units": getattr(no2_data, "units", "mol/m²")
        })
        
        # Guardar como Zarr
        output_path = DATA_DIR / TEMPO_CONFIG["zarr_path"]
        output_ds.to_zarr(output_path, mode="w")
        
        log_success(f"TEMPO NO₂ guardado en {output_path}")
        log_info(f"Dimensiones: {dict(output_ds.dims)}")
        
        return str(output_path)
        
    except Exception as e:
        log_error(f"Error descargando TEMPO: {e}")
        return None
    
    finally:
        # Cerrar datasets
        try:
            if 'ds' in locals():
                ds.close()
            if 'ds_cropped' in locals():
                ds_cropped.close()
        except:
            pass

def validate_tempo_data(zarr_path: str) -> bool:
    """Validar que los datos TEMPO se guardaron correctamente."""
    try:
        ds = xr.open_zarr(zarr_path)
        
        # Verificar que tiene la variable NO₂
        if TEMPO_CONFIG["output_name"] not in ds:
            log_error("Variable NO₂ no encontrada en archivo Zarr")
            return False
        
        # Verificar dimensiones mínimas
        no2_var = ds[TEMPO_CONFIG["output_name"]]
        if no2_var.size == 0:
            log_error("Dataset NO₂ está vacío")
            return False
        
        log_success(f"Validación TEMPO exitosa: {dict(ds.dims)}")
        return True
        
    except Exception as e:
        log_error(f"Error validando TEMPO: {e}")
        return False

if __name__ == "__main__":
    # Test standalone
    result = fetch_tempo_no2()
    if result:
        validate_tempo_data(result)
