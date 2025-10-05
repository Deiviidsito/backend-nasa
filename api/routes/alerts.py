"""
Endpoint /api/alerts - Lista celdas con risk_score > 66
"""
from fastapi import APIRouter, Query, HTTPException
from core.loader import get_dataset, get_dataset_bounds
import numpy as np
from datetime import datetime
from typing import List, Dict, Any

router = APIRouter(tags=["Alerts"])

@router.get(
    "/alerts",
    summary="Alertas de alta contaminación",
    description="Devuelve lista de celdas con risk_score > 66 (alto riesgo)"
)
async def get_alerts(
    threshold: float = Query(
        default=66.0,
        ge=0.0,
        le=100.0,
        description="Umbral de risk_score para alertas (default: 66)"
    ),
    format: str = Query(
        default="json",
        regex="^(json|geojson)$",
        description="Formato de respuesta"
    )
):
    """
    **Sistema de Alertas de Calidad del Aire**
    
    Identifica celdas que superan el umbral de riesgo especificado.
    
    Umbrales estándar:
    - 🟢 **0-33**: Bajo riesgo
    - 🟡 **34-66**: Riesgo moderado  
    - 🔴 **67-100**: Alto riesgo (ALERTA)
    
    Útil para:
    - 🚨 Sistemas de alerta temprana
    - 📱 Notificaciones push
    - 🏥 Advertencias de salud pública
    - 🚦 Control de tráfico
    """
    try:
        ds = get_dataset()
        bounds = get_dataset_bounds()
        current_time = datetime.utcnow()
        
        # Encontrar celdas que superan el umbral
        alert_cells = []
        
        for i, lat in enumerate(ds.lat.values):
            for j, lon in enumerate(ds.lon.values):
                risk_score = float(ds.risk_score.isel(lat=i, lon=j).values)
                
                # Solo celdas válidas que superan el umbral
                if not np.isnan(risk_score) and risk_score > threshold:
                    
                    # Determinar nivel de alerta
                    alert_level = get_alert_level(risk_score)
                    
                    cell = {
                        "lat": float(lat),
                        "lon": float(lon),
                        "risk_score": risk_score,
                        "risk_class": determine_risk_class(risk_score),
                        "alert_level": alert_level,
                        "cell_id": f"{i}_{j}",
                        "exceeded_by": risk_score - threshold,
                        "message": get_alert_message(risk_score)
                    }
                    
                    # Agregar variables contextuales
                    if "no2" in ds:
                        cell["no2"] = float(ds.no2.isel(lat=i, lon=j).values)
                    if "pm25" in ds:
                        cell["pm25"] = float(ds.pm25.isel(lat=i, lon=j).values)
                    if "o3" in ds:
                        cell["o3"] = float(ds.o3.isel(lat=i, lon=j).values)
                    
                    alert_cells.append(cell)
        
        # Ordenar por risk_score descendente (más críticos primero)
        alert_cells.sort(key=lambda x: x["risk_score"], reverse=True)
        
        # Generar respuesta según formato
        if format == "geojson":
            return create_alerts_geojson(alert_cells, bounds, threshold, current_time)
        else:
            return create_alerts_json(alert_cells, bounds, threshold, current_time)
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo alertas: {str(e)}"
        )

@router.get(
    "/alerts/summary",
    summary="Resumen de alertas",
    description="Estadísticas resumidas del estado de alertas"
)
async def get_alerts_summary():
    """Resumen ejecutivo de alertas activas."""
    try:
        ds = get_dataset()
        
        # Contar celdas por nivel de riesgo
        total_cells = 0
        high_risk = 0
        critical_risk = 0
        max_risk = 0
        
        for i, lat in enumerate(ds.lat.values):
            for j, lon in enumerate(ds.lon.values):
                risk_score = float(ds.risk_score.isel(lat=i, lon=j).values)
                
                if not np.isnan(risk_score):
                    total_cells += 1
                    max_risk = max(max_risk, risk_score)
                    
                    if risk_score > 66:
                        high_risk += 1
                        if risk_score > 80:
                            critical_risk += 1
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": get_overall_status(high_risk, critical_risk),
            "statistics": {
                "total_cells": total_cells,
                "high_risk_cells": high_risk,
                "critical_risk_cells": critical_risk,
                "percentage_high_risk": round((high_risk / total_cells) * 100, 1) if total_cells > 0 else 0,
                "max_risk_score": max_risk
            },
            "recommendations": get_recommendations(high_risk, critical_risk, max_risk)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo resumen de alertas: {str(e)}"
        )

def determine_risk_class(risk_score: float) -> str:
    """Determina clase de riesgo."""
    if np.isnan(risk_score):
        return "unknown"
    elif risk_score >= 67:
        return "high"
    elif risk_score >= 34:
        return "moderate"
    else:
        return "low"

def get_alert_level(risk_score: float) -> str:
    """Determina nivel de alerta específico."""
    if risk_score >= 90:
        return "critical"
    elif risk_score >= 80:
        return "severe"
    elif risk_score >= 67:
        return "high"
    else:
        return "moderate"

def get_alert_message(risk_score: float) -> str:
    """Genera mensaje de alerta apropiado."""
    if risk_score >= 90:
        return "🚨 CRÍTICO: Evitar actividades al aire libre"
    elif risk_score >= 80:
        return "⚠️ SEVERO: Limitar exposición exterior"
    elif risk_score >= 67:
        return "🔴 ALTO: Precaución en grupos sensibles"
    else:
        return "🟡 MODERADO: Monitoreo continuo"

def create_alerts_json(cells: List[Dict], bounds: Dict, threshold: float, timestamp: datetime) -> Dict[str, Any]:
    """Crea respuesta JSON para alertas."""
    return {
        "timestamp": timestamp.isoformat() + "Z",
        "alert_threshold": threshold,
        "total_alerts": len(cells),
        "bounds": bounds,
        "status": "active" if len(cells) > 0 else "clear",
        "alerts": cells,
        "summary": {
            "critical": len([c for c in cells if c["alert_level"] == "critical"]),
            "severe": len([c for c in cells if c["alert_level"] == "severe"]), 
            "high": len([c for c in cells if c["alert_level"] == "high"]),
            "max_risk": max([c["risk_score"] for c in cells]) if cells else 0
        }
    }

def create_alerts_geojson(cells: List[Dict], bounds: Dict, threshold: float, timestamp: datetime) -> Dict[str, Any]:
    """Crea respuesta GeoJSON para alertas."""
    features = []
    
    for cell in cells:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [cell["lon"], cell["lat"]]
            },
            "properties": {
                "risk_score": cell["risk_score"],
                "alert_level": cell["alert_level"],
                "message": cell["message"],
                "cell_id": cell["cell_id"],
                "color": get_alert_color(cell["alert_level"]),
                **{k: v for k, v in cell.items() if k not in ["lat", "lon"]}
            }
        })
    
    return {
        "type": "FeatureCollection",
        "properties": {
            "name": "CleanSky LA - Active Alerts",
            "timestamp": timestamp.isoformat() + "Z",
            "alert_threshold": threshold,
            "total_alerts": len(features),
            "bounds": bounds
        },
        "features": features
    }

def get_alert_color(alert_level: str) -> str:
    """Color para nivel de alerta."""
    colors = {
        "critical": "#8B0000",   # Rojo oscuro
        "severe": "#FF0000",     # Rojo
        "high": "#FF6600",       # Naranja
        "moderate": "#FFFF00"    # Amarillo
    }
    return colors.get(alert_level, "#808080")

def get_overall_status(high_risk: int, critical_risk: int) -> str:
    """Estado general del sistema."""
    if critical_risk > 0:
        return "critical"
    elif high_risk > 5:
        return "severe"
    elif high_risk > 0:
        return "alert"
    else:
        return "normal"

def get_recommendations(high_risk: int, critical_risk: int, max_risk: float) -> List[str]:
    """Recomendaciones basadas en el estado."""
    recommendations = []
    
    if critical_risk > 0:
        recommendations.extend([
            "Evitar actividades al aire libre",
            "Mantener ventanas cerradas",
            "Usar mascarillas N95 si es necesario salir"
        ])
    elif high_risk > 3:
        recommendations.extend([
            "Limitar ejercicio exterior",
            "Grupos sensibles deben permanecer en interiores"
        ])
    elif high_risk > 0:
        recommendations.extend([
            "Monitoreo continuo para grupos sensibles",
            "Considerar postponer actividades prolongadas al aire libre"
        ])
    else:
        recommendations.append("Condiciones normales - sin restricciones")
    
    return recommendations