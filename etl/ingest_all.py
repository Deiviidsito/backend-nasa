"""
Ejecuta toda la ingesta de datos CleanSky LA y guarda los datasets en /data/zarr_store/
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json

# Agregar el directorio padre al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from etl.ingest_tempo import fetch_tempo_no2, validate_tempo_data
from etl.ingest_openaq import fetch_latest_openaq, validate_openaq_data, get_openaq_summary
from etl.utils import log_info, log_error, log_success, ensure_data_dirs, get_recent_date_range

# Imports opcionales para meteorología
try:
    from etl.ingest_meteorology import (
        fetch_imerg_precip, fetch_merra2_wind_temp, 
        validate_meteorology_data
    )
    METEOROLOGY_AVAILABLE = True
except ImportError as e:
    log_info(f"Módulo meteorología no disponible: {e}")
    METEOROLOGY_AVAILABLE = False
    fetch_imerg_precip = None
    fetch_merra2_wind_temp = None
    validate_meteorology_data = None

def run_tempo_ingestion() -> Optional[str]:
    """Ejecutar ingesta TEMPO."""
    log_info("🛰️ Iniciando ingesta TEMPO (NO₂)...")
    
    try:
        result = fetch_tempo_no2()
        
        if result and validate_tempo_data(result):
            log_success("Ingesta TEMPO completada exitosamente")
            return result
        else:
            log_error("Fallo en ingesta TEMPO")
            return None
            
    except Exception as e:
        log_error(f"Error en ingesta TEMPO: {e}")
        return None

def run_openaq_ingestion() -> Optional[str]:
    """Ejecutar ingesta OpenAQ."""
    log_info("🌫️ Iniciando ingesta OpenAQ (estaciones terrestres)...")
    
    try:
        result = fetch_latest_openaq()
        
        if result and validate_openaq_data(result):
            log_success("Ingesta OpenAQ completada exitosamente")
            
            # Mostrar resumen
            summary = get_openaq_summary(result)
            if summary:
                log_info(f"Resumen OpenAQ: {summary['total_records']} registros, "
                        f"{summary['unique_locations']} ubicaciones, "
                        f"parámetros: {summary['parameters']}")
            
            return result
        else:
            log_error("Fallo en ingesta OpenAQ")
            return None
            
    except Exception as e:
        log_error(f"Error en ingesta OpenAQ: {e}")
        return None

def run_meteorology_ingestion() -> Dict[str, Optional[str]]:
    """Ejecutar ingesta meteorológica (opcional)."""
    results = {"imerg": None, "merra2": None}
    
    if not METEOROLOGY_AVAILABLE:
        log_info("🌧️ Módulo meteorología no disponible, saltando...")
        return results
    
    log_info("🌧️ Iniciando ingesta meteorológica (IMERG + MERRA-2)...")
    
    # IMERG Precipitación
    try:
        if fetch_imerg_precip:
            log_info("Descargando IMERG precipitación...")
            imerg_result = fetch_imerg_precip()
            
            if imerg_result and validate_meteorology_data(imerg_result, "imerg"):
                results["imerg"] = imerg_result
                log_success("IMERG completado")
            else:
                log_error("Fallo en IMERG")
                
    except Exception as e:
        log_error(f"Error en IMERG: {e}")
    
    # MERRA-2 Temperatura/Viento
    try:
        if fetch_merra2_wind_temp:
            log_info("Descargando MERRA-2 temperatura/viento...")
            merra2_result = fetch_merra2_wind_temp()
            
            if merra2_result and validate_meteorology_data(merra2_result, "merra2"):
                results["merra2"] = merra2_result
                log_success("MERRA-2 completado")
            else:
                log_error("Fallo en MERRA-2")
                
    except Exception as e:
        log_error(f"Error en MERRA-2: {e}")
    
    return results

def generate_ingestion_report(results: Dict[str, Any]) -> Dict[str, Any]:
    """Generar reporte de ingesta."""
    start_date, end_date = get_recent_date_range()
    
    report = {
        "ingestion_date": str(Path(__file__).stat().st_mtime),
        "date_range": {"start": start_date, "end": end_date},
        "datasets": {},
        "summary": {
            "total_datasets": 0,
            "successful": 0,
            "failed": 0
        }
    }
    
    # Procesar resultados
    for dataset_name, result in results.items():
        if result:
            report["datasets"][dataset_name] = {
                "status": "success",
                "path": result,
                "size_mb": round(Path(result).stat().st_size / (1024*1024), 2) if Path(result).exists() else 0
            }
            report["summary"]["successful"] += 1
        else:
            report["datasets"][dataset_name] = {
                "status": "failed",
                "path": None,
                "size_mb": 0
            }
            report["summary"]["failed"] += 1
        
        report["summary"]["total_datasets"] += 1
    
    return report

def save_ingestion_report(report: Dict[str, Any]) -> str:
    """Guardar reporte de ingesta."""
    ensure_data_dirs()
    report_path = Path(__file__).parent.parent / "data" / "ingestion_report.json"
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    log_info(f"Reporte guardado en: {report_path}")
    return str(report_path)

def run_all() -> Dict[str, Any]:
    """
    Ejecutar toda la ingesta de datos CleanSky LA.
    
    Returns:
        Diccionario con resultados de cada dataset
    """
    log_info("🚀 Iniciando ingesta completa de datos CleanSky Los Ángeles...")
    
    # Asegurar directorios
    ensure_data_dirs()
    
    # Resultados
    results = {}
    
    # 1. TEMPO NO₂ (satelital)
    tempo_result = run_tempo_ingestion()
    results["tempo"] = tempo_result
    
    # 2. OpenAQ (estaciones terrestres)
    openaq_result = run_openaq_ingestion()
    results["openaq"] = openaq_result
    
    # 3. Meteorología (opcional)
    met_results = run_meteorology_ingestion()
    results.update(met_results)
    
    # Generar reporte
    report = generate_ingestion_report(results)
    save_ingestion_report(report)
    
    # Resumen final
    successful = report["summary"]["successful"]
    total = report["summary"]["total_datasets"]
    
    if successful == total:
        log_success(f"✅ Ingesta completada exitosamente: {successful}/{total} datasets")
    elif successful > 0:
        log_info(f"⚠️ Ingesta parcialmente exitosa: {successful}/{total} datasets")
    else:
        log_error(f"❌ Ingesta fallida: {successful}/{total} datasets")
    
    # Mostrar archivos generados
    log_info("\n📂 Archivos generados:")
    for dataset, result in results.items():
        if result:
            size = Path(result).stat().st_size / (1024*1024) if Path(result).exists() else 0
            log_info(f"  ✅ {dataset}: {result} ({size:.1f} MB)")
        else:
            log_info(f"  ❌ {dataset}: FALLO")
    
    return results

def check_prerequisites() -> bool:
    """Verificar prerequisitos antes de ejecutar ingesta."""
    log_info("🔍 Verificando prerequisitos...")
    
    # Verificar credenciales EarthData
    import os
    username = os.getenv("EARTHDATA_USERNAME")
    password = os.getenv("EARTHDATA_PASSWORD")
    
    if not username or not password:
        log_error("❌ Credenciales NASA EarthData no configuradas")
        log_error("   Configura EARTHDATA_USERNAME y EARTHDATA_PASSWORD en .env")
        return False
    
    if username == "tu_usuario" or password == "tu_contraseña":
        log_error("❌ Credenciales NASA EarthData usando valores por defecto")
        log_error("   Actualiza las credenciales reales en .env")
        return False
    
    log_success("✅ Credenciales EarthData configuradas")
    
    # Verificar conectividad
    try:
        import requests
        response = requests.get("https://api.openaq.org/v3/latest", timeout=10)
        if response.status_code == 200:
            log_success("✅ Conectividad OpenAQ verificada")
        else:
            log_error(f"❌ Error conectividad OpenAQ: {response.status_code}")
            return False
    except Exception as e:
        log_error(f"❌ Error conectividad: {e}")
        return False
    
    log_success("✅ Prerequisitos verificados")
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingesta de datos CleanSky LA")
    parser.add_argument("--skip-check", action="store_true", 
                       help="Saltar verificación de prerequisitos")
    parser.add_argument("--only", choices=["tempo", "openaq", "meteorology"],
                       help="Ejecutar solo un tipo de ingesta")
    
    args = parser.parse_args()
    
    # Verificar prerequisitos (unless skipped)
    if not args.skip_check and not check_prerequisites():
        log_error("❌ Prerequisitos no cumplidos. Usa --skip-check para forzar.")
        sys.exit(1)
    
    # Ejecutar ingesta específica o completa
    if args.only == "tempo":
        result = run_tempo_ingestion()
        sys.exit(0 if result else 1)
    elif args.only == "openaq":
        result = run_openaq_ingestion()
        sys.exit(0 if result else 1)
    elif args.only == "meteorology":
        results = run_meteorology_ingestion()
        success = any(results.values())
        sys.exit(0 if success else 1)
    else:
        # Ingesta completa
        results = run_all()
        
        # Exit code basado en éxito
        successful_count = sum(1 for r in results.values() if r)
        sys.exit(0 if successful_count > 0 else 1)