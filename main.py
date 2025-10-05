from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import datetime as dt
from config import settings

app = FastAPI(
    title="CleanSky LA API",
    version="0.1.0",
    description="API para monitoreo y predicción de calidad del aire en Los Ángeles usando datos satelitales NASA",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (permitir frontend local y vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    """Endpoint raíz con información del sistema."""
    return {
        "name": "CleanSky LA API",
        "version": "0.1.0",
        "description": "Monitoreo de calidad del aire en Los Ángeles",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "latest": "/api/latest",
            "forecast": "/api/forecast",
            "alerts": "/api/alerts",
            "tiles": "/api/tiles/{z}/{x}/{y}.png",
        },
    }

@app.get("/health")
def health():
    """Health check endpoint con información del sistema."""
    earthdata_configured = settings.validate_earthdata_credentials()
    
    return {
        "status": "ok",
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
        "environment": {
            "debug_mode": settings.DEBUG,
            "earthdata_configured": earthdata_configured,
            "cors_origins": settings.CORS_ORIGINS if settings.DEBUG else ["configured"],
        },
        "configuration": {
            "bbox": settings.get_bbox_dict(),
            "grid_resolution": settings.GRID_RESOLUTION,
            "update_interval_minutes": settings.UPDATE_INTERVAL,
        },
        "data_sources": {
            "tempo": "NASA TEMPO (NO2, O3)",
            "openaq": "OpenAQ (PM2.5, NO2, O3)",
            "imerg": "NASA IMERG (Precipitation)",
            "merra2": "NASA MERRA-2 (Meteorology)",
        },
    }

# ---- Stubs de endpoints ----
@app.get("/api/latest")
def api_latest() -> Dict[str, Any]:
    # TODO: Reemplazar con lectura real (Zarr/DB). Respuesta de ejemplo.
    return {
        "bbox": [-118.7, 33.6, -117.8, 34.4],
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "grid_resolution_deg": 0.05,
        "variables": ["no2", "pm25", "o3", "temp", "wind", "rain"],
        "cells": [
            {"lat": 34.00, "lon": -118.30, "risk_score": 58, "class": "moderate"},
            {"lat": 34.05, "lon": -118.25, "risk_score": 71, "class": "bad"},
        ],
    }

@app.get("/api/forecast")
def api_forecast() -> Dict[str, Any]:
    horizon_hours = [1, 2, 3, 4, 5, 6]
    # TODO: Sustituir por modelo ML/Advección
    return {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "forecasts": [{"hour": h, "risk_score": max(0, min(100, 60 + h*2))} for h in horizon_hours],
    }

@app.get("/api/alerts")
def api_alerts() -> Dict[str, Any]:
    # TODO: Generar desde análisis de rejilla
    return {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "alerts": [
            {
                "level": "high",
                "risk_score": 72,
                "message": "Calidad del aire mala. Evite actividades al aire libre.",
                "centroid": {"lat": 34.05, "lon": -118.24},
            }
        ],
    }

@app.get("/api/tiles/{z}/{x}/{y}.png")
def api_tiles(z: int, x: int, y: int):
    # TODO: Render real de tiles. Por ahora retornamos 404 para indicar stub.
    raise HTTPException(status_code=404, detail="Tiles not implemented yet")
