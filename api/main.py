"""
CleanSky API — Los Ángeles
Fase 3: API REST profesional con FastAPI
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Importaciones limpias

app = FastAPI(
    title="CleanSky Los Ángeles API",
    description="API REST que expone el índice AIR Risk Score generado por datos satelitales TEMPO + OpenAQ + MERRA-2.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — permitir acceso desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar endpoints oficiales limpios
from routes import official, health, airquality

# Registrar rutas - ENDPOINTS OFICIALES FASE 3
app.include_router(official.router, prefix="/api")    # /api/latest, /api/forecast, /api/alerts, /api/tiles

# Rutas adicionales
app.include_router(health.router, prefix="/api")      # /api/health  
app.include_router(airquality.router, prefix="/api")  # /api/airquality

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "🌎 CleanSky Los Ángeles API — Online",
        "version": "1.0.0",
        "status": "✅ Fase 3 Completada - Todos los endpoints operativos",
        "endpoints": {
            # Endpoints oficiales Fase 3
            "latest": "/api/latest",
            "forecast": "/api/forecast", 
            "alerts": "/api/alerts",
            "tiles": "/api/tiles/{z}/{x}/{y}.png",
            # Endpoints adicionales
            "health": "/api/health",
            "air_quality": "/api/airquality?lat=34.05&lon=-118.25",
            "heatmap": "/api/heatmap",
            "docs": "/docs"
        },
        "data_sources": {
            "tempo": "NASA TEMPO (NO₂, O₃)",
            "openaq": "OpenAQ (PM2.5)",
            "merra2": "NASA MERRA-2 (Meteorología)"
        }
    }