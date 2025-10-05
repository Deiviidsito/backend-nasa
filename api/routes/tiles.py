"""
Endpoint /api/tiles - Tiles raster para mapas web
"""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from core.loader import get_dataset, get_dataset_bounds
import numpy as np
import io
from PIL import Image, ImageDraw
from typing import Tuple

router = APIRouter(tags=["Map Tiles"])

@router.get(
    "/tiles/{z}/{x}/{y}.png",
    summary="Tiles raster semáforo",
    description="Genera tiles PNG para mapas web con colores semáforo según risk_score"
)
async def get_tile(z: int, x: int, y: int):
    """
    **Tiles raster para mapas web**
    
    Genera tiles PNG de 256x256 píxeles con colores semáforo:
    - 🟢 Verde: risk_score 0-33 (bajo)
    - 🟡 Amarillo: risk_score 34-66 (moderado)  
    - 🔴 Rojo: risk_score 67-100 (alto)
    
    Compatible con:
    - 🍃 Leaflet
    - 🗺️ OpenLayers  
    - 📱 MapLibre GL
    
    **Parámetros:**
    - `z`: Zoom level (0-18)
    - `x`: Tile X coordinate
    - `y`: Tile Y coordinate
    """
    try:
        # Validar parámetros de tile
        if z < 0 or z > 18:
            raise HTTPException(status_code=400, detail="Zoom level debe estar entre 0 y 18")
        
        # Calcular bounding box del tile
        tile_bounds = tile_to_bbox(z, x, y)
        
        # Generar imagen del tile
        tile_image = generate_tile_image(tile_bounds, 256, 256)
        
        # Convertir a PNG
        img_buffer = io.BytesIO()
        tile_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return StreamingResponse(
            io.BytesIO(img_buffer.read()),
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache 1 hora
                "Content-Type": "image/png"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando tile: {str(e)}"
        )

@router.get(
    "/tiles/preview",
    summary="Preview del tile system",
    description="Genera una imagen de preview mostrando el grid completo"
)
async def get_tiles_preview():
    """Genera preview del sistema de tiles."""
    try:
        ds = get_dataset()
        bounds = get_dataset_bounds()
        
        # Generar imagen de preview 512x512
        preview_image = generate_preview_image(bounds, 512, 512)
        
        img_buffer = io.BytesIO()
        preview_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return StreamingResponse(
            io.BytesIO(img_buffer.read()),
            media_type="image/png"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando preview: {str(e)}"
        )

def tile_to_bbox(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Convierte coordenadas de tile a bounding box geográfico."""
    n = 2.0 ** z
    
    # Calcular límites del tile en coordenadas geográficas
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    
    north_rad = np.arctan(np.sinh(np.pi * (1 - 2 * y / n)))
    south_rad = np.arctan(np.sinh(np.pi * (1 - 2 * (y + 1) / n)))
    
    north = np.degrees(north_rad)
    south = np.degrees(south_rad)
    
    return west, south, east, north

def generate_tile_image(tile_bounds: Tuple[float, float, float, float], width: int, height: int) -> Image.Image:
    """Genera imagen PNG para un tile específico."""
    west, south, east, north = tile_bounds
    
    # Crear imagen base transparente
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    try:
        ds = get_dataset()
        dataset_bounds = get_dataset_bounds()
        
        # Verificar si el tile intersecta con nuestros datos
        if (east < dataset_bounds["lon_min"] or west > dataset_bounds["lon_max"] or
            north < dataset_bounds["lat_min"] or south > dataset_bounds["lat_max"]):
            # Tile fuera del área de datos - retornar transparente
            return image
        
        # Interpolar datos del dataset al grid del tile
        for i in range(0, width, 16):  # Muestrear cada 16 píxeles para performance
            for j in range(0, height, 16):
                # Convertir coordenadas de píxel a geográficas
                lon = west + (east - west) * (i / width)
                lat = north - (south - north) * (j / height)
                
                # Verificar si está dentro de nuestros datos
                if (dataset_bounds["lon_min"] <= lon <= dataset_bounds["lon_max"] and
                    dataset_bounds["lat_min"] <= lat <= dataset_bounds["lat_max"]):
                    
                    try:
                        # Interpolar risk_score
                        data_point = ds.sel(lat=lat, lon=lon, method='nearest')
                        risk_score = float(data_point["risk_score"].values)
                        
                        if not np.isnan(risk_score):
                            # Obtener color basado en risk_score
                            color = get_risk_color_rgba(risk_score)
                            
                            # Dibujar rectángulo de 16x16
                            draw.rectangle(
                                [i, j, min(i+16, width), min(j+16, height)],
                                fill=color
                            )
                    except:
                        continue  # Ignorar errores de interpolación
        
        return image
        
    except Exception as e:
        # En caso de error, retornar imagen con mensaje
        draw.text((10, 10), f"Error: {str(e)[:50]}", fill=(255, 0, 0, 255))
        return image

def generate_preview_image(bounds: dict, width: int, height: int) -> Image.Image:
    """Genera imagen de preview del dataset completo."""
    image = Image.new('RGB', (width, height), (240, 240, 240))  # Fondo gris claro
    draw = ImageDraw.Draw(image)
    
    try:
        ds = get_dataset()
        
        # Dibujar grid del dataset
        for i, lat in enumerate(ds.lat.values):
            for j, lon in enumerate(ds.lon.values):
                risk_score = float(ds.risk_score.isel(lat=i, lon=j).values)
                
                if not np.isnan(risk_score):
                    # Convertir coordenadas geográficas a píxeles
                    x = int((lon - bounds["lon_min"]) / (bounds["lon_max"] - bounds["lon_min"]) * width)
                    y = int((bounds["lat_max"] - lat) / (bounds["lat_max"] - bounds["lat_min"]) * height)
                    
                    # Tamaño de celda
                    cell_w = width // 20  # Aproximado para 20 columnas
                    cell_h = height // 15  # Aproximado para 15 filas
                    
                    # Color basado en risk_score
                    color = get_risk_color_rgb(risk_score)
                    
                    # Dibujar celda
                    draw.rectangle(
                        [x - cell_w//2, y - cell_h//2, x + cell_w//2, y + cell_h//2],
                        fill=color,
                        outline=(0, 0, 0)
                    )
        
        # Agregar leyenda
        draw.text((10, 10), "CleanSky LA - Risk Grid Preview", fill=(0, 0, 0))
        draw.text((10, 30), "🟢 Low (0-33)  🟡 Moderate (34-66)  🔴 High (67-100)", fill=(0, 0, 0))
        
        return image
        
    except Exception as e:
        draw.text((10, 50), f"Error: {str(e)}", fill=(255, 0, 0))
        return image

def get_risk_color_rgba(risk_score: float) -> Tuple[int, int, int, int]:
    """Retorna color RGBA basado en risk_score."""
    if risk_score >= 67:
        return (255, 0, 0, 180)    # Rojo semi-transparente
    elif risk_score >= 34:
        return (255, 255, 0, 180)  # Amarillo semi-transparente
    else:
        return (0, 255, 0, 180)    # Verde semi-transparente

def get_risk_color_rgb(risk_score: float) -> Tuple[int, int, int]:
    """Retorna color RGB basado en risk_score."""
    if risk_score >= 67:
        return (255, 0, 0)    # Rojo
    elif risk_score >= 34:
        return (255, 255, 0)  # Amarillo
    else:
        return (0, 255, 0)    # Verde