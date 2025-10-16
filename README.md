# Reserva Espacios Backend

API REST para el sistema de reserva de espacios desarrollada con Flask.

## Requisitos

- Python 3.13+
- Docker (opcional)

## Instalación Local

1. Clonar el repositorio:
```bash
git clone <url-del-repositorio>
cd reserva-espacios-backend
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Configuración

La aplicación utiliza Pydantic Settings para la configuración. Puedes crear un archivo `.env` en la raíz del proyecto:

```env
# Configuración de la aplicación
FLASK_APP_NAME=Reserva Espacios Backend
FLASK_DEBUG=True
FLASK_SECRET_KEY=tu-clave-secreta-aqui

# Configuración del servidor
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Configuración de logging
FLASK_LOG_LEVEL=INFO
```

### Variables de entorno disponibles

- `FLASK_APP_NAME`: Nombre de la aplicación (default: "Reserva Espacios Backend")
- `FLASK_DEBUG`: Modo debug (default: False)
- `FLASK_SECRET_KEY`: Clave secreta para la aplicación
- `FLASK_HOST`: Host del servidor (default: "0.0.0.0")
- `FLASK_PORT`: Puerto del servidor (default: 5000)
- `FLASK_DATABASE_URL`: URL de la base de datos (default: "sqlite:///reserva_espacios.db")
- `FLASK_LOG_LEVEL`: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Ejecución

### Local
```bash
python src/app.py
```

### Docker
```bash
docker-compose up
```

La aplicación estará disponible en `http://localhost:5000`

## Endpoints Disponibles

### `GET /`
Mensaje de bienvenida del servicio.

**Respuesta:**
```json
{
  "message": "Hello World!",
  "status": "success"
}
```

### `GET /health`
Verificación del estado del servicio.

**Respuesta:**
```json
{
  "status": "healthy",
  "service": "Reserva Espacios Backend",
  "uptime": "running",
  "log_level": "INFO"
}
```

## Estructura del Proyecto

```
reserva-espacios-backend/
├── src/
│   ├── app.py          # Aplicación Flask principal
│   └── config.py       # Configuración con Pydantic
├── docker-compose.yaml # Configuración de Docker
├── Dockerfile.dev      # Imagen de Docker para desarrollo
├── requirements.txt    # Dependencias de Python
└── README.md          # Este archivo
```

## Desarrollo

El proyecto incluye configuraciones específicas para diferentes entornos:

- **Desarrollo**: `DevelopmentSettings` (DEBUG=True, LOG_LEVEL=DEBUG)
- **Producción**: `ProductionSettings` (DEBUG=False, LOG_LEVEL=INFO)
- **Testing**: `TestingSettings` (Base de datos en memoria)

Para usar una configuración específica, establece la variable de entorno `FLASK_ENVIRONMENT`:

```bash
export FLASK_ENVIRONMENT=production
python src/app.py
```
