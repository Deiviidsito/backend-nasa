#!/usr/bin/env python3
"""
Script de testing rápido para el Dashboard CleanSky
Muestra estadísticas de los datos generados y abre el dashboard
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import webbrowser
import time
import subprocess
import sys
from pathlib import Path

class DashboardTester:
    """Tester para el dashboard con datos generados"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.backend_dir = Path(__file__).parent
    
    async def test_api_endpoints(self):
        """Prueba todos los endpoints importantes"""
        
        print("🧪 Probando endpoints del API CleanSky...")
        
        endpoints = {
            "root": "/",
            "health": "/health", 
            "dashboard_all": "/api/dashboard/all-data",
            "dashboard_metrics": "/api/dashboard/metrics",
            "cities": "/api/cities"
        }
        
        async with aiohttp.ClientSession() as session:
            for name, endpoint in endpoints.items():
                try:
                    url = f"{self.base_url}{endpoint}"
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            print(f"  ✅ {name}: {response.status}")
                            
                            # Mostrar datos específicos
                            if name == "dashboard_all":
                                await self.analyze_dashboard_data(data)
                            elif name == "cities":
                                cities_count = len(data.get("cities", []))
                                print(f"     📊 {cities_count} ciudades disponibles")
                        else:
                            print(f"  ❌ {name}: {response.status}")
                            
                except Exception as e:
                    print(f"  🔥 {name}: Error - {str(e)}")
    
    async def analyze_dashboard_data(self, data):
        """Analiza los datos del dashboard"""
        
        print("    📊 Análisis de datos del dashboard:")
        
        # Metadata
        metadata = data.get("metadata", {})
        print(f"     📅 Última actualización: {metadata.get('last_update', 'N/A')}")
        print(f"     🏙️  Total ciudades: {metadata.get('total_cities', 0)}")
        
        # Status de ciudades
        cities_status = data.get("cities_status", {})
        success_cities = sum(1 for status in cities_status.values() if status == "success")
        print(f"     ✅ Ciudades con datos: {success_cities}/{len(cities_status)}")
        
        # Datos del mapa
        map_data = data.get("map_data", {})
        features = map_data.get("features", [])
        print(f"     📍 Puntos en el mapa: {len(features):,}")
        
        if features:
            # Analizar distribución de AQI
            aqi_values = []
            for feature in features[:1000]:  # Sample de 1000 puntos
                props = feature.get("properties", {})
                if "aqi" in props:
                    aqi_values.append(props["aqi"])
            
            if aqi_values:
                avg_aqi = sum(aqi_values) / len(aqi_values)
                max_aqi = max(aqi_values)
                min_aqi = min(aqi_values)
                print(f"     🎯 AQI promedio: {avg_aqi:.1f}")
                print(f"     📈 AQI rango: {min_aqi:.1f} - {max_aqi:.1f}")
        
        # Datos tabulares
        tabular_data = data.get("tabular_data", [])
        print(f"     📋 Filas en tabla: {len(tabular_data):,}")
        
        # Resumen por ciudad
        city_summaries = data.get("city_summaries", {})
        if city_summaries:
            print(f"     🌆 Resúmenes de ciudad: {len(city_summaries)}")
            
            # Mostrar top 3 ciudades por AQI
            city_aqis = []
            for city_id, summary in city_summaries.items():
                aqi = summary.get("average_aqi", 0)
                city_name = summary.get("name", city_id)
                city_aqis.append((city_name, aqi))
            
            city_aqis.sort(key=lambda x: x[1], reverse=True)
            
            print("     🔝 Top 3 ciudades con mayor AQI:")
            for i, (city, aqi) in enumerate(city_aqis[:3], 1):
                print(f"        {i}. {city}: {aqi:.1f}")
    
    def check_server_status(self):
        """Verifica si el servidor está corriendo"""
        
        try:
            import requests
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_server_if_needed(self):
        """Inicia el servidor si no está corriendo"""
        
        if not self.check_server_status():
            print("🚀 Iniciando servidor...")
            
            # Cambiar al directorio del backend
            import os
            os.chdir(self.backend_dir)
            
            # Iniciar uvicorn en background
            subprocess.Popen([
                "uvicorn", "main:app", 
                "--host", "127.0.0.1", 
                "--port", "8000",
                "--reload"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Esperar que inicie
            print("⏳ Esperando que el servidor inicie...")
            for i in range(10):
                time.sleep(1)
                if self.check_server_status():
                    print("✅ Servidor iniciado correctamente")
                    return True
                print(f"   Esperando... {i+1}/10")
            
            print("❌ Error: No se pudo iniciar el servidor")
            return False
        else:
            print("✅ Servidor ya está corriendo")
            return True
    
    def open_dashboard_urls(self):
        """Abre las URLs útiles en el navegador"""
        
        urls = {
            "API Docs": f"{self.base_url}/docs",
            "Dashboard Data": f"{self.base_url}/api/dashboard/all-data",
            "Cities": f"{self.base_url}/api/cities",
            "Health": f"{self.base_url}/health"
        }
        
        print("🌐 URLs disponibles:")
        for name, url in urls.items():
            print(f"   {name}: {url}")
        
        # Abrir docs automáticamente
        try:
            webbrowser.open(urls["API Docs"])
            print("🚀 Abriendo documentación del API en el navegador...")
        except:
            print("⚠️ No se pudo abrir el navegador automáticamente")
    
    def show_data_summary(self):
        """Muestra resumen de los datos generados"""
        
        # Leer el reporte de datos generados
        report_file = self.backend_dir / "data" / "multi_city_processed" / "dashboard_sample_data_report.json"
        
        if report_file.exists():
            with open(report_file, 'r') as f:
                report = json.load(f)
            
            print("📊 Resumen de datos generados:")
            
            global_stats = report.get("global_stats", {})
            print(f"   📍 Total puntos: {global_stats.get('total_points', 0):,}")
            print(f"   🏙️  Total ciudades: {len(report.get('cities', {}))}")
            print(f"   🎯 AQI promedio: {global_stats.get('average_aqi', 0):.1f}")
            
            # Mostrar ciudades por categoría de riesgo  
            cities_by_risk = global_stats.get("cities_by_risk", {})
            if cities_by_risk:
                print("   📈 Distribución por riesgo:")
                for risk_level, cities in cities_by_risk.items():
                    if cities:
                        print(f"     {risk_level.title()}: {len(cities)} ciudades ({', '.join(cities)})")
        else:
            print("⚠️ No se encontró reporte de datos generados")

async def main():
    """Función principal del tester"""
    
    print("🎯 CleanSky Dashboard Tester")
    print("=" * 50)
    
    tester = DashboardTester()
    
    # 1. Mostrar resumen de datos
    tester.show_data_summary()
    print()
    
    # 2. Verificar/iniciar servidor
    if not tester.start_server_if_needed():
        print("❌ No se pudo iniciar el servidor. Terminando...")
        return
    print()
    
    # 3. Probar endpoints
    await tester.test_api_endpoints()
    print()
    
    # 4. Mostrar URLs
    tester.open_dashboard_urls()
    print()
    
    print("🎉 Testing completado!")
    print()
    print("💡 Próximos pasos:")
    print("   1. Ve a http://127.0.0.1:8000/docs para explorar el API")
    print("   2. Usa http://127.0.0.1:8000/api/dashboard/all-data para tu dashboard")
    print("   3. Los datos están en data/multi_city_processed/")
    print()
    print("🚀 Tu dashboard puede conectarse a estos endpoints!")

if __name__ == "__main__":
    asyncio.run(main())