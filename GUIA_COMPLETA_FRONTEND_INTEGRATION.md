# 🌍 CleanSky North America - Guía Completa de Integración Frontend

**Proyecto:** CleanSky Multi-Ciudad API Integration  
**Fecha:** 5 de Octubre de 2025  
**Backend API:** http://localhost:8000  
**Tipo:** Nueva implementación frontend con datos satelitales TEMPO  

---

## 📋 **Índice**

1. [🎯 Resumen del Proyecto](#resumen)
2. [🔗 Endpoints API Disponibles](#endpoints)
3. [⚙️ Configuración Inicial](#configuracion)
4. [🗺️ Implementación del Mapa](#mapa)
5. [📊 Dashboard de Comparación](#dashboard)
6. [🎨 Estilos y UI](#estilos)
7. [🧪 Testing y Validación](#testing)
8. [🚀 Deployment](#deployment)

---

## 🎯 **Resumen del Proyecto** {#resumen}

CleanSky North America es una plataforma de monitoreo de calidad del aire que utiliza datos satelitales NASA TEMPO para mostrar información en tiempo real de 6 ciudades principales de Estados Unidos.

### **Datos Técnicos:**
- **6 ciudades activas**: Los Angeles, New York, Chicago, Houston, Seattle, Miami
- **300 puntos de grilla por ciudad** (~3km resolución)
- **1,800 puntos totales** across North America
- **Tiempo respuesta**: < 400ms promedio
- **Formato**: GeoJSON nativo para mapas

### **Variables Disponibles:**
- `risk_score`: Índice de riesgo (0-100)
- `no2`: Dióxido de nitrógeno (NASA TEMPO)
- `o3`: Ozono troposférico
- `pm25`: Partículas PM2.5
- `temp`: Temperatura (MERRA-2)
- `wind`: Velocidad del viento

---

## 🔗 **Endpoints API Disponibles** {#endpoints}

### **Base URL:** `http://localhost:8000/api`

#### **1. Lista de Ciudades**
```http
GET /api/cities
```

**Respuesta:**
```json
{
  "total_cities": 10,
  "cities": [
    {
      "id": "los_angeles",
      "name": "Los Angeles, CA",
      "bbox": {
        "west": -118.7,
        "south": 33.6,
        "east": -117.8,
        "north": 34.4
      },
      "population": 3971883,
      "timezone": "America/Los_Angeles",
      "has_data": true,
      "grid_resolution": 0.03
    }
    // ... más ciudades
  ],
  "coverage": "North America (TEMPO coverage area)"
}
```

#### **2. Datos por Ciudad (JSON)**
```http
GET /api/cities/{city_id}/latest
```

**Ejemplo:**
```http
GET /api/cities/chicago/latest
```

**Respuesta:**
```json
{
  "city_id": "chicago",
  "city_name": "Chicago, IL",
  "timestamp": "2025-10-05T06:00:00Z",
  "grid_info": {
    "total_cells": 300,
    "bounds": {
      "west": -88.0,
      "south": 41.6,
      "east": -87.5,
      "north": 42.1
    }
  },
  "cells": [
    {
      "lat": 41.88,
      "lon": -87.63,
      "risk_score": 35.3,
      "risk_class": "moderate",
      "cell_id": "12_15",
      "no2": 0.000015,
      "pm25": 12.5,
      "o3": 0.000042,
      "temp": 289.2,
      "wind": 3.2
    }
    // ... 299 puntos más
  ],
  "summary": {
    "high_risk": 0,
    "moderate_risk": 169,
    "low_risk": 131
  }
}
```

#### **3. Datos GeoJSON (Para Mapas)**
```http
GET /api/cities/{city_id}/latest?format=geojson
```

**Respuesta:**
```json
{
  "type": "FeatureCollection",
  "properties": {
    "name": "CleanSky - Chicago, IL",
    "city_id": "chicago",
    "timestamp": "2025-10-05T06:00:00Z",
    "total_features": 300
  },
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-87.63, 41.88]
      },
      "properties": {
        "risk_score": 35.3,
        "risk_class": "moderate",
        "cell_id": "12_15",
        "no2": 0.000015,
        "pm25": 12.5,
        "o3": 0.000042,
        "temp": 289.2,
        "wind": 3.2
      }
    }
    // ... más features
  ]
}
```

#### **4. Comparación Multi-Ciudad**
```http
GET /api/compare?cities=los_angeles,new_york,chicago,houston
```

**Respuesta:**
```json
{
  "timestamp": "2025-10-05T06:00:00Z",
  "comparison_type": "air_quality_ranking",
  "cities_compared": 4,
  "cities_with_data": 4,
  "ranking": [
    {
      "city_id": "chicago",
      "city_name": "Chicago, IL",
      "population": 2693976,
      "avg_risk_score": 35.3,
      "max_risk_score": 67.2,
      "min_risk_score": 12.1,
      "high_risk_percentage": 0.0,
      "moderate_risk_percentage": 56.3,
      "low_risk_percentage": 43.7,
      "overall_class": "moderate",
      "total_grid_points": 300
    }
    // ... más ciudades
  ]
}
```

#### **5. Consulta por Coordenadas**
```http
GET /api/cities/{city_id}/airquality?lat={lat}&lon={lon}
```

**Ejemplo:**
```http
GET /api/cities/los_angeles/airquality?lat=34.05&lon=-118.24
```

#### **6. Alertas por Ciudad**
```http
GET /api/cities/{city_id}/alerts?threshold=70
```

---

## ⚙️ **Configuración Inicial** {#configuracion}

### **1. Estructura del Proyecto**

```
src/
├── components/
│   ├── CitySelector.jsx
│   ├── AirQualityMap.jsx
│   ├── CityComparison.jsx
│   ├── Dashboard.jsx
│   └── Alerts.jsx
├── hooks/
│   ├── useCityData.js
│   ├── useCityList.js
│   └── useComparison.js
├── utils/
│   ├── api.js
│   └── mapHelpers.js
├── styles/
│   ├── global.css
│   ├── map.css
│   └── dashboard.css
└── App.jsx
```

### **2. Configuración API**

```javascript
// utils/api.js
const API_BASE = 'http://localhost:8000/api';

export const api = {
  // Lista de ciudades
  getCities: async () => {
    const response = await fetch(`${API_BASE}/cities`);
    if (!response.ok) throw new Error('Error fetching cities');
    return response.json();
  },

  // Datos de una ciudad (JSON)
  getCityData: async (cityId) => {
    const response = await fetch(`${API_BASE}/cities/${cityId}/latest`);
    if (!response.ok) throw new Error(`Error fetching data for ${cityId}`);
    return response.json();
  },

  // Datos GeoJSON para mapas
  getCityGeoJSON: async (cityId) => {
    const response = await fetch(`${API_BASE}/cities/${cityId}/latest?format=geojson`);
    if (!response.ok) throw new Error(`Error fetching GeoJSON for ${cityId}`);
    return response.json();
  },

  // Comparar ciudades
  compareCities: async (cityIds) => {
    const cities = Array.isArray(cityIds) ? cityIds.join(',') : cityIds;
    const response = await fetch(`${API_BASE}/compare?cities=${cities}`);
    if (!response.ok) throw new Error('Error comparing cities');
    return response.json();
  },

  // Calidad del aire por coordenadas
  getAirQualityAtPoint: async (cityId, lat, lon) => {
    const response = await fetch(`${API_BASE}/cities/${cityId}/airquality?lat=${lat}&lon=${lon}`);
    if (!response.ok) throw new Error('Error fetching air quality at point');
    return response.json();
  },

  // Alertas
  getCityAlerts: async (cityId, threshold = 70) => {
    const response = await fetch(`${API_BASE}/cities/${cityId}/alerts?threshold=${threshold}`);
    if (!response.ok) throw new Error(`Error fetching alerts for ${cityId}`);
    return response.json();
  }
};

export default api;
```

### **3. Hook para Lista de Ciudades**

```javascript
// hooks/useCityList.js
import { useState, useEffect } from 'react';
import api from '../utils/api';

export function useCityList() {
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCities = async () => {
      try {
        setLoading(true);
        const data = await api.getCities();
        setCities(data.cities);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Error loading cities:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchCities();
  }, []);

  const activeCities = cities.filter(city => city.has_data);
  const pendingCities = cities.filter(city => !city.has_data);

  return {
    cities,
    activeCities,
    pendingCities,
    loading,
    error,
    totalCities: cities.length,
    activeCitiesCount: activeCities.length
  };
}
```

### **4. Hook para Datos de Ciudad**

```javascript
// hooks/useCityData.js
import { useState, useEffect } from 'react';
import api from '../utils/api';

export function useCityData(cityId, format = 'json') {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!cityId) return;
    
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const result = format === 'geojson' 
          ? await api.getCityGeoJSON(cityId)
          : await api.getCityData(cityId);
          
        setData(result);
      } catch (err) {
        setError(err.message);
        console.error(`Error loading data for ${cityId}:`, err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [cityId, format]);

  return { data, loading, error };
}
```

---

## 🗺️ **Implementación del Mapa** {#mapa}

### **1. Instalación de Dependencias**

```bash
npm install react-leaflet leaflet
# o
yarn add react-leaflet leaflet
```

### **2. Configuración de Leaflet**

```javascript
// utils/mapHelpers.js
import L from 'leaflet';

// Configuración de íconos de Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Centros de ciudades
export const CITY_CENTERS = {
  'los_angeles': [34.05, -118.25],
  'new_york': [40.71, -74.01],
  'chicago': [41.88, -87.63],
  'houston': [29.76, -95.37],
  'seattle': [47.61, -122.33],
  'miami': [25.76, -80.19]
};

// Bounds por ciudad
export const CITY_BOUNDS = {
  'los_angeles': [[-118.7, 33.6], [-117.8, 34.4]],
  'new_york': [[-74.3, 40.4], [-73.7, 41.0]],
  'chicago': [[-88.0, 41.6], [-87.5, 42.1]],
  'houston': [[-95.8, 29.5], [-95.0, 30.1]],
  'seattle': [[-122.5, 47.4], [-122.1, 47.8]],
  'miami': [[-80.4, 25.6], [-80.0, 26.0]]
};

// Función para obtener color según risk_score
export function getRiskColor(riskScore) {
  if (riskScore >= 67) return '#ef4444'; // Rojo - Bad
  if (riskScore >= 34) return '#f97316'; // Naranja - Moderate  
  return '#22c55e'; // Verde - Good
}

// Función para obtener texto de clasificación
export function getRiskClass(riskScore) {
  if (riskScore >= 67) return 'Mala';
  if (riskScore >= 34) return 'Moderada';
  return 'Buena';
}
```

### **3. Selector de Ciudad**

```jsx
// components/CitySelector.jsx
import React from 'react';
import { useCityList } from '../hooks/useCityList';

export function CitySelector({ selectedCity, onCityChange }) {
  const { activeCities, loading, error } = useCityList();

  if (loading) return <div className="city-selector-loading">Cargando ciudades...</div>;
  if (error) return <div className="city-selector-error">Error: {error}</div>;

  return (
    <div className="city-selector">
      <label htmlFor="city-select" className="city-selector-label">
        🌍 Seleccionar Ciudad:
      </label>
      <select
        id="city-select"
        value={selectedCity}
        onChange={(e) => onCityChange(e.target.value)}
        className="city-selector-dropdown"
      >
        <option value="">-- Selecciona una ciudad --</option>
        {activeCities.map(city => (
          <option key={city.id} value={city.id}>
            {city.name} ({city.population.toLocaleString()} hab)
          </option>
        ))}
      </select>
      <div className="city-selector-info">
        {activeCities.length} ciudades con datos disponibles
      </div>
    </div>
  );
}
```

### **4. Componente Principal del Mapa**

```jsx
// components/AirQualityMap.jsx
import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import { useCityData } from '../hooks/useCityData';
import { CitySelector } from './CitySelector';
import { CITY_CENTERS, CITY_BOUNDS, getRiskColor, getRiskClass } from '../utils/mapHelpers';
import 'leaflet/dist/leaflet.css';

export function AirQualityMap() {
  const [selectedCity, setSelectedCity] = useState('los_angeles');
  const { data: geoJsonData, loading, error } = useCityData(selectedCity, 'geojson');
  const [map, setMap] = useState(null);

  // Actualizar vista del mapa cuando cambia la ciudad
  useEffect(() => {
    if (map && selectedCity && CITY_BOUNDS[selectedCity]) {
      map.fitBounds(CITY_BOUNDS[selectedCity], { padding: [20, 20] });
    }
  }, [map, selectedCity]);

  const pointToLayer = (feature, latlng) => {
    const riskScore = feature.properties.risk_score;
    const color = getRiskColor(riskScore);
    
    return L.circleMarker(latlng, {
      radius: 6,
      fillColor: color,
      color: '#ffffff',
      weight: 1,
      opacity: 1,
      fillOpacity: 0.8
    });
  };

  const onEachFeature = (feature, layer) => {
    const props = feature.properties;
    const temp = props.temp ? (props.temp - 273.15).toFixed(1) : 'N/A';
    
    const popupContent = `
      <div class="map-popup">
        <h3>📊 Calidad del Aire</h3>
        <div class="risk-score" style="color: ${getRiskColor(props.risk_score)}">
          <strong>Risk Score: ${props.risk_score.toFixed(1)}</strong>
        </div>
        <p><strong>Clasificación:</strong> ${getRiskClass(props.risk_score)}</p>
        <hr>
        <p><strong>NO₂:</strong> ${(props.no2 * 1e9).toFixed(2)} ppb</p>
        <p><strong>O₃:</strong> ${(props.o3 * 1e9).toFixed(2)} ppb</p>
        <p><strong>PM2.5:</strong> ${props.pm25?.toFixed(1) || 'N/A'} μg/m³</p>
        <p><strong>Temperatura:</strong> ${temp}°C</p>
        <p><strong>Viento:</strong> ${props.wind?.toFixed(1) || 'N/A'} m/s</p>
        <hr>
        <small>Datos: NASA TEMPO, OpenAQ, MERRA-2</small>
      </div>
    `;
    
    layer.bindPopup(popupContent);
  };

  if (error) {
    return (
      <div className="map-error">
        <h3>❌ Error cargando datos</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="air-quality-map-container">
      <div className="map-controls">
        <CitySelector 
          selectedCity={selectedCity}
          onCityChange={setSelectedCity}
        />
        
        {loading && (
          <div className="map-loading">
            ⏳ Cargando datos de {selectedCity}...
          </div>
        )}

        {geoJsonData && (
          <div className="map-stats">
            <span className="stat-item">
              📍 {geoJsonData.properties.total_features} puntos de datos
            </span>
            <span className="stat-item">
              📊 Ciudad: {geoJsonData.properties.name.replace('CleanSky - ', '')}
            </span>
          </div>
        )}
      </div>

      <MapContainer
        center={CITY_CENTERS[selectedCity] || CITY_CENTERS.los_angeles}
        zoom={10}
        className="leaflet-map"
        ref={setMap}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {geoJsonData && !loading && (
          <GeoJSON
            data={geoJsonData}
            pointToLayer={pointToLayer}
            onEachFeature={onEachFeature}
            key={selectedCity} // Forzar re-render cuando cambia ciudad
          />
        )}
      </MapContainer>

      {/* Leyenda */}
      <div className="map-legend">
        <h4>📊 Leyenda de Calidad del Aire</h4>
        <div className="legend-items">
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#22c55e' }}></span>
            <span>Buena (0-34)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#f97316' }}></span>
            <span>Moderada (34-67)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#ef4444' }}></span>
            <span>Mala (67-100)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## 📊 **Dashboard de Comparación** {#dashboard}

### **1. Hook para Comparación**

```javascript
// hooks/useComparison.js
import { useState, useEffect } from 'react';
import api from '../utils/api';

export function useComparison(cityIds = []) {
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!cityIds.length) return;

    const fetchComparison = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.compareCities(cityIds);
        setComparison(data);
      } catch (err) {
        setError(err.message);
        console.error('Error fetching comparison:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchComparison();
  }, [cityIds.join(',')]);

  return { comparison, loading, error };
}
```

### **2. Componente de Comparación**

```jsx
// components/CityComparison.jsx
import React, { useState } from 'react';
import { useComparison } from '../hooks/useComparison';
import { useCityList } from '../hooks/useCityList';
import { getRiskClass } from '../utils/mapHelpers';

export function CityComparison() {
  const [selectedCities, setSelectedCities] = useState(['los_angeles', 'new_york', 'chicago', 'houston']);
  const { activeCities } = useCityList();
  const { comparison, loading, error } = useComparison(selectedCities);

  const handleCityToggle = (cityId) => {
    setSelectedCities(prev => 
      prev.includes(cityId) 
        ? prev.filter(id => id !== cityId)
        : [...prev, cityId]
    );
  };

  const getRankEmoji = (rank) => {
    const emojis = { 1: '🥇', 2: '🥈', 3: '🥉' };
    return emojis[rank] || `#${rank}`;
  };

  return (
    <div className="city-comparison">
      <div className="comparison-header">
        <h2>🏆 Ranking de Calidad del Aire</h2>
        <p>Comparación entre ciudades basada en datos satelitales NASA TEMPO</p>
      </div>

      {/* Selector de ciudades */}
      <div className="city-checkboxes">
        <h3>Seleccionar ciudades para comparar:</h3>
        <div className="checkbox-grid">
          {activeCities.map(city => (
            <label key={city.id} className="checkbox-item">
              <input
                type="checkbox"
                checked={selectedCities.includes(city.id)}
                onChange={() => handleCityToggle(city.id)}
              />
              <span>{city.name}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Resultados */}
      {loading && <div className="comparison-loading">⏳ Comparando ciudades...</div>}
      {error && <div className="comparison-error">❌ Error: {error}</div>}

      {comparison && (
        <div className="comparison-results">
          <div className="comparison-stats">
            <span>🌍 {comparison.cities_compared} ciudades comparadas</span>
            <span>📊 {comparison.cities_with_data} con datos válidos</span>
            <span>⏱️ {new Date(comparison.timestamp).toLocaleString()}</span>
          </div>

          <div className="ranking-grid">
            {comparison.ranking.map((city, index) => (
              <div key={city.city_id} className={`city-rank-card rank-${city.rank || index + 1}`}>
                <div className="rank-badge">
                  {getRankEmoji(city.rank || index + 1)}
                </div>
                
                <div className="city-info">
                  <h3>{city.city_name}</h3>
                  <div className="population">
                    👥 {city.population?.toLocaleString() || 'N/A'} habitantes
                  </div>
                </div>

                <div className="risk-metrics">
                  <div className="main-score">
                    <span className="score-value">{city.avg_risk_score.toFixed(1)}</span>
                    <span className="score-label">Risk Score Promedio</span>
                  </div>
                  
                  <div className="classification">
                    <span className={`class-badge class-${city.overall_class}`}>
                      {getRiskClass(city.avg_risk_score)}
                    </span>
                  </div>
                </div>

                <div className="detailed-stats">
                  <div className="stat-row">
                    <span className="stat-label">🔴 Alto Riesgo:</span>
                    <span className="stat-value">{city.high_risk_percentage.toFixed(1)}%</span>
                  </div>
                  <div className="stat-row">
                    <span className="stat-label">🟡 Moderado:</span>
                    <span className="stat-value">{city.moderate_risk_percentage.toFixed(1)}%</span>
                  </div>
                  <div className="stat-row">
                    <span className="stat-label">🟢 Bajo Riesgo:</span>
                    <span className="stat-value">{city.low_risk_percentage.toFixed(1)}%</span>
                  </div>
                </div>

                <div className="range-info">
                  <small>
                    Rango: {city.min_risk_score.toFixed(1)} - {city.max_risk_score.toFixed(1)}
                    <br />
                    📍 {city.total_grid_points} puntos de datos
                  </small>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

### **3. Dashboard Principal**

```jsx
// components/Dashboard.jsx
import React, { useState } from 'react';
import { AirQualityMap } from './AirQualityMap';
import { CityComparison } from './CityComparison';

export function Dashboard() {
  const [activeTab, setActiveTab] = useState('map');

  const tabs = [
    { id: 'map', label: '🗺️ Mapa', component: <AirQualityMap /> },
    { id: 'comparison', label: '🏆 Comparación', component: <CityComparison /> }
  ];

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>🌍 CleanSky North America</h1>
          <p>Monitoreo de calidad del aire con datos satelitales NASA TEMPO</p>
          <div className="header-stats">
            <span className="stat">🛰️ 6 Ciudades Activas</span>
            <span className="stat">📊 1,800 Puntos de Datos</span>
            <span className="stat">⚡ Tiempo Real</span>
          </div>
        </div>
      </header>

      <nav className="dashboard-nav">
        <div className="nav-tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="dashboard-content">
        {tabs.find(tab => tab.id === activeTab)?.component}
      </main>

      <footer className="dashboard-footer">
        <div className="footer-content">
          <p>
            <strong>Fuentes de Datos:</strong> 
            NASA TEMPO (NO₂), OpenAQ (Ground Stations), MERRA-2 (Meteorología)
          </p>
          <p>
            <strong>Desarrollado para:</strong> NASA Space Apps Challenge 2024
          </p>
        </div>
      </footer>
    </div>
  );
}
```

### **4. App Principal**

```jsx
// App.jsx
import React from 'react';
import { Dashboard } from './components/Dashboard';
import './styles/global.css';
import './styles/map.css';
import './styles/dashboard.css';

function App() {
  return (
    <div className="App">
      <Dashboard />
    </div>
  );
}

export default App;
```

---

## 🎨 **Estilos CSS** {#estilos}

### **1. Estilos Globales**

```css
/* styles/global.css */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  background-color: #f8fafc;
  color: #1f2937;
  line-height: 1.6;
}

.dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Header */
.dashboard-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem 0;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  text-align: center;
}

.dashboard-header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

.header-stats {
  display: flex;
  justify-content: center;
  gap: 2rem;
  flex-wrap: wrap;
}

.header-stats .stat {
  background: rgba(255, 255, 255, 0.2);
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
}

/* Navigation */
.dashboard-nav {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 1rem;
}

.nav-tabs {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  gap: 0;
}

.nav-tab {
  background: none;
  border: none;
  padding: 1rem 2rem;
  font-size: 1rem;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
}

.nav-tab.active {
  border-bottom-color: #667eea;
  color: #667eea;
}

/* Content */
.dashboard-content {
  flex: 1;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
  width: 100%;
}

/* Footer */
.dashboard-footer {
  background: #374151;
  color: white;
  padding: 1.5rem 0;
  margin-top: auto;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  text-align: center;
  font-size: 0.9rem;
}
```

### **2. Estilos del Mapa**

```css
/* styles/map.css */
.air-quality-map-container {
  position: relative;
  height: 70vh;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.map-controls {
  position: absolute;
  top: 1rem;
  left: 1rem;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.city-selector {
  background: white;
  padding: 1rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  min-width: 250px;
}

.city-selector-dropdown {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
}

.leaflet-map {
  height: 100%;
  width: 100%;
}

.map-legend {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  background: white;
  padding: 1rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 1000;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  margin-bottom: 0.25rem;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 50%;
}
```

### **3. Estilos del Dashboard**

```css
/* styles/dashboard.css */
.city-comparison {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.comparison-header {
  text-align: center;
  margin-bottom: 2rem;
}

.city-checkboxes {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 8px;
}

.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  padding: 0.5rem;
}

.ranking-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.city-rank-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  position: relative;
}

.rank-badge {
  position: absolute;
  top: -10px;
  right: 1rem;
  background: #667eea;
  color: white;
  padding: 0.5rem;
  border-radius: 50%;
  font-size: 1.2rem;
  min-width: 40px;
  text-align: center;
}

.city-rank-card.rank-1 {
  border-left: 4px solid #ffd700;
}

.main-score {
  text-align: center;
  margin-bottom: 0.5rem;
}

.score-value {
  display: block;
  font-size: 2rem;
  font-weight: bold;
  color: #374151;
}

.class-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

.class-badge.class-moderate {
  background: #fef3c7;
  color: #92400e;
}

.detailed-stats {
  border-top: 1px solid #e5e7eb;
  padding-top: 1rem;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}
```

---

## 🧪 **Testing y Validación** {#testing}

### **1. Test de Conectividad**

```javascript
// utils/testConnection.js
import api from './api';

export async function testApiConnection() {
  const tests = [
    {
      name: 'Lista de ciudades',
      test: () => api.getCities(),
      validate: (data) => data.cities && data.cities.length > 0
    },
    {
      name: 'Datos de Los Angeles',
      test: () => api.getCityData('los_angeles'),
      validate: (data) => data.cells && data.cells.length >= 100
    },
    {
      name: 'GeoJSON de Chicago',  
      test: () => api.getCityGeoJSON('chicago'),
      validate: (data) => data.type === 'FeatureCollection' && data.features.length >= 100
    },
    {
      name: 'Comparación ciudades',
      test: () => api.compareCities(['los_angeles', 'chicago']),
      validate: (data) => data.ranking && data.ranking.length === 2
    }
  ];

  console.log('🧪 Iniciando tests de conectividad API...');
  
  for (const test of tests) {
    try {
      console.log(`Testing: ${test.name}...`);
      const result = await test.test();
      
      if (test.validate(result)) {
        console.log(`✅ ${test.name}: PASS`);
      } else {
        console.log(`❌ ${test.name}: FAIL - Datos inválidos`);
      }
    } catch (error) {
      console.log(`❌ ${test.name}: ERROR - ${error.message}`);
    }
  }
  
  console.log('🏁 Tests completados');
}

// Ejecutar en consola: testApiConnection()
```

---

## 🚀 **Deployment** {#deployment}

### **1. Variables de Entorno**

```javascript
// .env.local
REACT_APP_API_BASE_URL=http://localhost:8000/api
REACT_APP_ENVIRONMENT=development
```

### **2. Build de Producción**

```bash
# Instalar dependencias
npm install

# Build para producción
npm run build

# Servir localmente
npm start
```

---

## 📝 **Resumen de Implementación**

### **✅ Funcionalidades Implementadas:**

1. **🗺️ Mapa Interactivo**
   - Selector de 6 ciudades
   - 300 puntos por ciudad con datos satelitales
   - Popups con información detallada
   - Leyenda de colores por risk score

2. **📊 Dashboard de Comparación**
   - Ranking automático de ciudades
   - Métricas detalladas por ciudad
   - Selección múltiple de ciudades
   - Estadísticas de calidad del aire

3. **🔗 Integración API Completa**
   - Todos los endpoints implementados
   - Manejo de errores y loading states
   - Hooks reutilizables para datos
   - Testing de conectividad

### **🎯 Ready to Use:**

Tu frontend está completamente preparado para conectarse a la API CleanSky North America y mostrar datos de calidad del aire de 6 ciudades principales usando datos satelitales NASA TEMPO.

**¡CleanSky North America Frontend listo para NASA Space Apps Challenge!** 🌍🛰️✨

---

*Desarrollado para NASA Space Apps Challenge 2024*  
*CleanSky: Satellite Air Quality Platform*