"""Stub de ingesta OpenAQ (PM2.5, NO2, O3)."""
import requests

def fetch_latest_openaq(bbox: str = "-118.7,33.6,-117.8,34.4"):
    url = f"https://api.openaq.org/v3/latest?bbox={bbox}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()
