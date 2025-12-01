# Reserva Espacios Backend

API REST para el sistema de reserva de espacios desarrollada con Flask y SQLAlchemy.

## Requisitos

- Python 3.13+
- PostgreSQL (base de datos principal)
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

La aplicación utiliza Pydantic Settings ([documentación](https://docs.pydantic.dev/2.12/concepts/pydantic_settings)) para la configuración. Puedes crear un archivo `.env` en la raíz del proyecto:

```env
# Configuración de la aplicación
FLASK_APP_NAME=Reserva Espacios Backend
FLASK_DEBUG=True
FLASK_SECRET_KEY=tu-clave-secreta-aqui

# Configuración del servidor
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Configuración de base de datos
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/reserva_espacios_um
DATABASE_ECHO=False
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Configuración de logging
FLASK_LOG_LEVEL=INFO
```

### Variables de entorno disponibles

- `FLASK_APP_NAME`: Nombre de la aplicación (default: "Reserva Espacios Backend")
- `FLASK_DEBUG`: Modo debug (default: False)
- `FLASK_SECRET_KEY`: Clave secreta para la aplicación
- `FLASK_HOST`: Host del servidor (default: "0.0.0.0")
- `FLASK_PORT`: Puerto del servidor (default: 5000)
- `DATABASE_URL`: URL de conexión a PostgreSQL (default: "postgresql://postgres:postgres@localhost:5432/reserva_espacios_um")
- `DATABASE_ECHO`: Mostrar queries SQL en logs (default: False)
- `DATABASE_POOL_SIZE`: Tamaño del pool de conexiones (default: 5)
- `DATABASE_MAX_OVERFLOW`: Overflow máximo del pool (default: 10)
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

### `GET /health`
Verificación del estado del servicio y conectividad con la base de datos.

**Respuesta:**
```json
{
  "status": "healthy",
  "message": "Servicio funcionando correctamente",
  "uptime": "running",
  "database": {
    "status": "healthy",
    "message": "Base de datos conectada correctamente"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### `GET /spaces`
Endpoints relacionados con espacios (en desarrollo).

**Respuesta:**
```json
{
  "message": "Hello World!",
  "status": "success"
}
```

## Modelos de Datos

### Zone (Zona)
Representa una zona donde se ubican los espacios:
- `id`: Identificador único
- `name`: Nombre de la zona
- `description`: Descripción opcional
- `color`: Color en formato hex (#RRGGBB)
- `price`: Precio base para la zona
- `active`: Estado activo/inactivo
- `created_at`, `updated_at`: Timestamps

### Space (Espacio)
Representa un espacio físico disponible para reservar:
- `id`: Identificador único
- `name`: Nombre del espacio
- `zone_id`: ID de la zona a la que pertenece
- `price`: Precio del espacio
- `width`: Ancho en píxeles
- `height`: Alto en píxeles
- `x_coordinate`, `y_coordinate`: Posición en el plano
- `active`: Estado activo/inactivo
- `created_at`, `updated_at`: Timestamps

## Estructura del Proyecto

```
reserva-espacios-backend/
├── src/
│   ├── app.py              # Aplicación Flask principal
│   ├── config.py           # Configuración con Pydantic
│   ├── database.py         # Configuración de SQLAlchemy
│   ├── health/
│   │   └── routes.py       # Endpoints de health-check
│   ├── spaces/
│   │   ├── models/
│   │   │   ├── space.py    # Modelo Space
│   │   │   └── zone.py     # Modelo Zone
│   │   └── routes.py       # Endpoints de espacios
│   └── utils/
│       └── db_utils.py     # Utilidades de base de datos
├── docker-compose.yaml     # Configuración de Docker
├── Dockerfile.dev          # Imagen de Docker para desarrollo
├── requirements.txt        # Dependencias de Python
└── README.md              # Este archivo
```

## Desarrollo

El proyecto incluye configuraciones específicas para diferentes entornos:

- **Desarrollo**: `DevelopmentSettings` (DEBUG=True, LOG_LEVEL=DEBUG)
- **Producción**: `ProductionSettings` (DEBUG=False, LOG_LEVEL=INFO)
- **Testing**: `TestingSettings` (Base de datos en memoria SQLite)

Para usar una configuración específica, establece la variable de entorno `FLASK_ENVIRONMENT`:

```bash
export FLASK_ENVIRONMENT=production
python src/app.py
```

## Base de Datos

La aplicación utiliza PostgreSQL como base de datos principal con SQLAlchemy como ORM. Las migraciones se gestionan con Alembic.

### Migraciones con Alembic

El proyecto utiliza [Alembic](https://alembic.sqlalchemy.org/) para gestionar las migraciones de la base de datos. Alembic está configurado para usar la variable de entorno `DATABASE_URL`.

#### Comandos básicos

```bash
# Navegar al directorio src
cd src

# Generar migración automática (detecta cambios en modelos)
alembic revision --autogenerate -m "Descripción del cambio"

# Aplicar migraciones pendientes
alembic upgrade head

# Ver estado actual
alembic current

# Ver historial de migraciones
alembic history

# Revertir a migración anterior
alembic downgrade -1

# Revertir a migración específica
alembic downgrade <revision_id>
```

#### Flujo de trabajo típico

1. Modificar/agregar modelo
2. **Si es un modelo nuevo**: Importarlo en `src/alembic/env.py`
3. **Generar migración**: `alembic revision --autogenerate -m "Descripción"`
4. **Revisar archivo generado** en `alembic/versions/`
5. **Aplicar migración**: `alembic upgrade head`

#### Importar modelos nuevos

Cuando agregues un nuevo modelo, debes importarlo en `alembic/env.py` para que Alembic lo detecte:

```python
# En src/alembic/env.py
from spaces.models.space import Space
from spaces.models.zone import Zone
from modulox.models.nuevo_modelo import NuevoModelo  # ← Agregar aquí
```

#### Documentación oficial

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Tutorial de Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Autogenerate Documentation](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)

### Utilidades de Base de Datos

El módulo `utils/db_utils.py` proporciona funciones para:
- Verificar conectividad con la base de datos
- Obtener información del pool de conexiones
- Inicializar y eliminar tablas
- Ejecutar consultas SQL de forma segura
