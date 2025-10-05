"""Fusión de satelital + estaciones y cálculo de risk_score (stub)."""
import numpy as np

def minmax(a):
    a = np.asarray(a, dtype=float)
    return (a - np.nanmin(a)) / (np.nanmax(a) - np.nanmin(a) + 1e-9)

def compute_risk(no2, o3, pm25, temp, windspd, aerosol_idx):
    return (0.30*minmax(no2) + 0.25*minmax(o3) + 0.20*minmax(pm25) +
            0.10*minmax(temp) + 0.10*(windspd < 2.0).astype(float) +
            0.05*minmax(aerosol_idx)) * 100.0
