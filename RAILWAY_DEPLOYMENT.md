# 🚀 CleanSky North America - Railway Deployment

## Deployment en Railway

### ⚡ Quick Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

### 🔧 Variables de Entorno Requeridas

Configura estas variables en Railway Dashboard:

```bash
# NASA EarthData (Requerido para datos satelitales)
EARTHDATA_USERNAME=tu_usuario_nasa
EARTHDATA_PASSWORD=tu_contraseña_nasa

# Configuración de API
DEBUG=False
CORS_ORIGINS=https://tu-frontend.vercel.app,https://tu-dominio.com

# Opcional
OPENAQ_API_KEY=tu_api_key_openaq
```

### 📝 Pasos de Deployment

1. **Fork el repositorio** en GitHub
2. **Conectar con Railway:**
   - Ve a [railway.app](https://railway.app)
   - Crea nuevo proyecto desde GitHub
   - Selecciona este repositorio

3. **Configurar variables de entorno:**
   - Panel de Railway > Variables
   - Agregar las variables listadas arriba

4. **Deploy automático:**
   - Railway detectará `railway.toml` y `Procfile`
   - Build y deploy automático en ~2-3 minutos

### 🌐 Endpoints Disponibles

Después del deploy:

```
https://tu-app.railway.app/              # API Info
https://tu-app.railway.app/docs          # Swagger UI
https://tu-app.railway.app/api/cities    # Lista ciudades
```

### 🎯 Test de Funcionamiento

```bash
# Test básico
curl https://tu-app.railway.app/

# Test ciudades
curl https://tu-app.railway.app/api/cities

# Test datos
curl "https://tu-app.railway.app/api/cities/los_angeles/latest"
```

### 🔍 Troubleshooting

#### Error 500 en startup:
- Verificar variables `EARTHDATA_USERNAME` y `EARTHDATA_PASSWORD`
- Chequear logs en Railway Dashboard

#### CORS Error:
- Agregar dominio del frontend a `CORS_ORIGINS`
- Formato: `https://dominio1.com,https://dominio2.com`

#### Datos vacíos:
- API funcionará sin datos NASA si faltan credenciales
- Generará datos demo para testing

### 📊 Configuración Automática

- **Port:** Railway asigna automáticamente (`$PORT`)
- **Environment:** Detecta `RAILWAY_ENVIRONMENT=production`
- **Build:** Nixpacks con Python 3.11
- **Health check:** Endpoint `/`
- **Restart:** Automático en fallos

### 🚦 Status

- ✅ **FastAPI**: Configurado para producción
- ✅ **Multi-ciudad**: 6 ciudades Norte América
- ✅ **CORS**: Configurado para frontends
- ✅ **Health checks**: Habilitados
- ✅ **Auto-restart**: Configurado
- ✅ **Logs**: Disponibles en Railway

---

**🌍 CleanSky North America - Ready for Production!**