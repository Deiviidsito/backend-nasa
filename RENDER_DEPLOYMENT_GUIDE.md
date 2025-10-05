# 🚀 CleanSky North America - Render Deployment Guide

## ⚡ Deploy en Render - Pasos Exactos

### 1️⃣ **Preparación del Repositorio**
✅ Tu código ya está listo en GitHub: `Deiviidsito/backend-nasa`  
✅ Branch: `main` (o el branch que prefieras)  
✅ Archivos de configuración creados  

### 2️⃣ **Crear Web Service en Render**

1. **Ve a [render.com](https://render.com)**
2. **Haz clic en "New +"** → **"Web Service"**
3. **Conecta tu repositorio GitHub:**
   - Repository: `Deiviidsito/backend-nasa`
   - Branch: `main`

### 3️⃣ **Configuración del Servicio**

**Configuración Básica:**
```
Name: cleansky-north-america
Region: Oregon (US West)
Branch: main
Runtime: Python 3
```

**Build & Deploy:**
```
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Instance Type:**
```
Free (512MB RAM, 0.1 CPU)
```

### 4️⃣ **Variables de Entorno**

En la sección "Environment" de Render, agrega:

```bash
# Configuración básica
DEBUG=False
PORT=10000

# CORS (agregar tu dominio de frontend)
CORS_ORIGINS=https://tu-frontend.vercel.app,https://localhost:3000

# NASA EarthData (REQUERIDO para datos reales)
EARTHDATA_USERNAME=tu_usuario_nasa
EARTHDATA_PASSWORD=tu_contraseña_nasa

# Opcional - OpenAQ
OPENAQ_API_KEY=tu_api_key_opcional
```

### 5️⃣ **Deploy Automático**

Render iniciará el deploy automáticamente:
- ⏱️ **Tiempo estimado:** 3-5 minutos
- 📦 **Instala dependencias** automáticamente
- 🚀 **Inicia tu API** en el puerto asignado
- 🌐 **Asigna URL pública:** `https://cleansky-north-america.onrender.com`

### 6️⃣ **Verificar Deployment**

Una vez que el deploy termine (status: "Live"):

```bash
# Test básico
curl https://cleansky-north-america.onrender.com/

# Test ciudades
curl https://cleansky-north-america.onrender.com/api/cities

# Test datos específicos
curl "https://cleansky-north-america.onrender.com/api/cities/los_angeles/latest"
```

### 7️⃣ **Endpoints Disponibles**

Tu API estará disponible en:
```
https://cleansky-north-america.onrender.com/              # Info API
https://cleansky-north-america.onrender.com/docs          # Swagger UI
https://cleansky-north-america.onrender.com/api/cities    # Lista ciudades
https://cleansky-north-america.onrender.com/api/cities/los_angeles/latest # Datos LA
https://cleansky-north-america.onrender.com/api/compare?cities=los_angeles,chicago # Comparar
```

---

## 🔧 **Configuración Avanzada**

### Auto-Deploy
- ✅ **Activado por defecto** - Deploy automático en cada push
- 🔄 **Branch tracking** - Solo deploys del branch seleccionado

### Health Checks
- ✅ **Endpoint:** `/` (configurado automáticamente)
- ⏱️ **Timeout:** 60 segundos
- 🔄 **Reinicio automático** si falla

### Logs
- 📊 **Logs en tiempo real** en el dashboard de Render
- 🐛 **Debug** fácil con logs detallados

---

## 🚨 **Troubleshooting**

### ❌ Build Fails
**Problema:** Error instalando dependencias
**Solución:** 
- Verificar `requirements.txt` está bien formateado
- Asegurar Python 3.11 compatible

### ❌ Start Command Fails
**Problema:** Error al iniciar uvicorn
**Solución:**
- Verificar `main.py` existe
- Confirmar que FastAPI app se llama `app`

### ❌ 500 Internal Server Error
**Problema:** Error en runtime
**Solución:**
- Revisar logs en Render dashboard
- Verificar variables de entorno
- Comprobar importaciones de módulos

### ❌ CORS Errors
**Problema:** Frontend no puede conectar
**Solución:**
- Agregar dominio frontend a `CORS_ORIGINS`
- Formato: `https://dominio1.com,https://dominio2.com`

---

## 📊 **Plan Gratuito de Render**

✅ **750 horas/mes** (suficiente para desarrollo)  
✅ **512MB RAM** (adecuado para FastAPI)  
✅ **SSL automático** (HTTPS gratis)  
✅ **Dominio incluido** (.onrender.com)  
✅ **Auto-deploy** desde GitHub  
❗ **Hibernación** después de 15 min inactividad  

---

## 🎯 **Ready para Deploy**

¡Tu proyecto CleanSky North America está 100% listo para Render!

**Siguiente paso:** Ve a render.com y sigue la guía paso a paso.

**URL esperada:** `https://cleansky-north-america.onrender.com`

---

🌍 **CleanSky North America - NASA Space Apps Challenge 2024** 🛰️