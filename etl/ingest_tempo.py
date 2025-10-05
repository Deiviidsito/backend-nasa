"""Stub de ingesta TEMPO.
Reemplaza este archivo con lógica real usando earthaccess/harmony para descargar/streaming.
"""
from typing import Tuple

BBOX_LA = (-118.7, 33.6, -117.8, 34.4)

def fetch_tempo_no2(bbox: Tuple[float, float, float, float] = BBOX_LA):
    # TODO: usar earthaccess.search_data(...) y abrir con xarray
    print("Descargando NO2 TEMPO para bbox:", bbox)
    return None
