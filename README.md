# Reserva Espacios Backend

API REST para el sistema de reserva de espacios para la Feria de Empleo, desarrollada con Flask, SQLAlchemy y Keycloak.

## Requisitos previos

- [Docker](https://www.docker.com/) y Docker Compose
- Node.js 18+ (solo para el frontend)

El backend, la base de datos y Keycloak corren todos dentro de Docker, no es necesario instalar Python localmente.

---

## Cómo levantar el proyecto

### 1. Configurar variables de entorno

Crear un archivo `.env` en la raíz de `reserva-espacios-backend/` con el siguiente contenido:

```env
# Aplicación
FLASK_APP_NAME=Reserva Espacios Backend
FLASK_DEBUG=True
FLASK_SECRET_KEY=cambia-esto-por-un-string-secreto

# Servidor
FLASK_HOST=0.0.0.0
FLASK_PORT=5001

# Base de datos (usar estos valores si se usa Docker Compose)
DATABASE_URL=postgresql://postgres:postgres@postgres-db:5432/reserva_espacios_um
DATABASE_ECHO=False
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Keycloak
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=reserva-espacios
KEYCLOAK_CLIENT_ID=front-admin
KEYCLOAK_ISSUER_URL=http://localhost:8080

# Storage de archivos (ver sección "Configurar almacenamiento" más abajo)
AWS_ACCESS_KEY_ID=tu-access-key
AWS_SECRET_ACCESS_KEY=tu-secret-key
AWS_S3_BUCKET_NAME=nombre-de-tu-bucket
AWS_S3_REGION=sa-east-1
```

> **Importante:** nunca subas el archivo `.env` al repositorio. Asegurate de que esté en el `.gitignore`.

### 2. Levantar con Docker Compose

```bash
cd reserva-espacios-backend
docker compose up
```

Esto levanta automáticamente:

| Servicio    | Puerto | Descripción                          |
|-------------|--------|--------------------------------------|
| PostgreSQL  | 5432   | Base de datos principal              |
| Keycloak    | 8080   | Servidor de autenticación            |
| Backend API | 5001   | API REST de Flask                    |

Keycloak importa el realm `reserva-espacios` automáticamente desde `reserva-espacios-realm.json`.

### 3. Levantar el frontend

```bash
cd reserva-espacios-front
cp .env.example .env   # o crear el archivo manualmente (ver abajo)
npm install
npm run dev
```

El frontend queda disponible en `http://localhost:5173`.

**Variables de entorno del frontend (`.env`):**

```env
VITE_KEYCLOAK_URL=http://localhost:8080
VITE_KEYCLOAK_REALM=reserva-espacios
VITE_KEYCLOAK_CLIENT_ID=front-admin
VITE_API_BASE=http://localhost:5001
```

---

## Configurar almacenamiento de archivos

El sistema usa un servicio de storage para guardar las imágenes de los planos. Soporta tres proveedores:

| Proveedor | Cambios de código | Cambios de config |
|---|---|---|
| **AWS S3** | Ninguno | Solo `.env` |
| **DigitalOcean Spaces** | Ninguno | Solo `.env` |
| **Azure Blob Storage** | 3 archivos | `.env` |

---

### Opción A — AWS S3

1. Crear un bucket S3 en AWS.
2. Crear un usuario IAM con permisos `s3:PutObject` y `s3:GetObject` sobre ese bucket.
3. Configurar el `.env`:

```env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET_NAME=nombre-del-bucket
AWS_S3_REGION=us-east-1
# S3_ENDPOINT_URL no se define (dejar vacío o comentado)
```

---

### Opción B — DigitalOcean Spaces

DigitalOcean Spaces tiene una API compatible con S3, por lo que **no requiere cambios de código**. Solo hay que agregar `S3_ENDPOINT_URL` al `.env`:

1. Crear un Space en DigitalOcean y obtener las credenciales (Access Key + Secret Key) desde **API → Spaces Keys**.
2. Configurar el `.env`:

```env
AWS_ACCESS_KEY_ID=clave-de-spaces
AWS_SECRET_ACCESS_KEY=secret-de-spaces
AWS_S3_BUCKET_NAME=nombre-del-space
AWS_S3_REGION=nyc3   # la región del Space: nyc3, sfo3, ams3, sgp1, etc.
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com   # reemplazar con la región correcta
```

Las URLs públicas generadas tendrán el formato `https://<bucket>.<region>.digitaloceanspaces.com/<key>`.

---

### Opción C — Azure Blob Storage

Azure no es compatible con la API de S3, por lo que requiere cambios en **3 archivos**:

#### 1. `requirements.txt`

Reemplazar:
```
boto3==1.42.34
```
Por:
```
azure-storage-blob==12.x.x
```

#### 2. `src/services/s3_service.py`

Reemplazar toda la implementación:

```python
import uuid
from io import BytesIO
from azure.storage.blob import BlobServiceClient, ContentSettings
from config import settings

def _get_container_client():
    client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
    return client.get_container_client(settings.AZURE_CONTAINER_NAME)

def get_file(blob_key: str) -> tuple[bytes | None, str | None, str | None]:
    try:
        blob_client = _get_container_client().get_blob_client(blob_key)
        data = blob_client.download_blob().readall()
        props = blob_client.get_blob_properties()
        content_type = props.content_settings.content_type or "application/octet-stream"
        return data, content_type, None
    except Exception as e:
        return None, None, f"Error al obtener archivo: {e}"

def upload_file(file_data, original_filename: str, content_type: str = None) -> str:
    extension = original_filename.rsplit(".", 1)[-1] if "." in original_filename else ""
    blob_name = f"planos/{uuid.uuid4()}.{extension}" if extension else f"planos/{uuid.uuid4()}"
    file_bytes = file_data.read()
    try:
        blob_client = _get_container_client().get_blob_client(blob_name)
        cs = ContentSettings(content_type=content_type) if content_type else None
        blob_client.upload_blob(BytesIO(file_bytes), content_settings=cs)
        service = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        url = f"https://{service.account_name}.blob.core.windows.net/{settings.AZURE_CONTAINER_NAME}/{blob_name}"
        return url
    except Exception as e:
        raise Exception(f"Error al subir archivo: {e}")
```

#### 3. `reserva-espacios-front/src/utils/imageProxy.ts`

Actualizar el regex para detectar URLs de Azure:

```typescript
// Reemplazar esta línea:
const S3_URL_PATTERN = /^https:\/\/([^.]+)\.s3\.([^.]+)\.amazonaws\.com\/(.+)$/;

// Por esta:
const AZURE_URL_PATTERN = /^https:\/\/([^.]+)\.blob\.core\.windows\.net\/([^/]+)\/(.+)$/;

// Y actualizar toProxyUrl:
export function toProxyUrl(url: string): string {
    if (!url || url.startsWith('data:') || url.startsWith(API_BASE)) return url;
    const match = url.match(AZURE_URL_PATTERN);
    if (match) {
        const blobKey = `${match[2]}/${match[3]}`;
        return `${API_BASE}/planos/image/${blobKey}`;
    }
    return url;
}
```

#### Variables de entorno para Azure

Reemplazar las variables `AWS_*` en el `.env` por:

```env
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net
AZURE_CONTAINER_NAME=nombre-del-contenedor
```

También agregar estas dos variables al modelo `Settings` en `src/config.py`:

```python
AZURE_STORAGE_CONNECTION_STRING: str | None = Field(default=None)
AZURE_CONTAINER_NAME: str | None = Field(default=None)
```

> El resto del sistema (rutas, proxy de imágenes, canvas del frontend) **no necesita cambios** porque el storage está abstraído detrás de `s3_service.py`.

---

## Estructura del proyecto

```
reserva-espacios-backend/
├── src/
│   ├── app.py                  # Punto de entrada Flask
│   ├── config.py               # Variables de entorno (Pydantic Settings)
│   ├── database.py             # Configuración SQLAlchemy
│   ├── services/
│   │   └── s3_service.py       # Abstracción de storage de archivos
│   ├── auth/                   # Decoradores JWT / Keycloak
│   ├── eventos/                # Gestión de eventos
│   ├── planos/                 # Planos de planta + endpoints de imágenes
│   ├── spaces/                 # Espacios individuales
│   ├── zones/                  # Zonas
│   ├── reservas/               # Reservas
│   ├── user_profiles/          # Perfiles de usuario
│   ├── websocket/              # WebSocket (Flask-SocketIO)
│   └── alembic/                # Migraciones de base de datos
├── keycloak-theme/             # Tema personalizado de Keycloak
├── reserva-espacios-realm.json # Configuración del realm de Keycloak
├── docker-compose.yaml
├── Dockerfile.dev
├── requirements.txt
└── .env                        # No subir al repositorio
```

---

## Migraciones de base de datos

Las migraciones se gestionan con Alembic:

```bash
cd src

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Generar migración a partir de cambios en modelos
alembic revision --autogenerate -m "descripción"

# Ver estado actual
alembic current
```

---

## Variables de entorno — referencia completa

| Variable | Descripción | Default |
|---|---|---|
| `FLASK_SECRET_KEY` | Clave secreta de la app | — |
| `FLASK_DEBUG` | Modo debug | `False` |
| `FLASK_HOST` | Host del servidor | `0.0.0.0` |
| `FLASK_PORT` | Puerto del servidor | `5001` |
| `DATABASE_URL` | URL de conexión PostgreSQL | — |
| `KEYCLOAK_URL` | URL interna de Keycloak (dentro de Docker) | — |
| `KEYCLOAK_REALM` | Nombre del realm | `reserva-espacios` |
| `KEYCLOAK_CLIENT_ID` | Client ID de Keycloak | `front-admin` |
| `KEYCLOAK_ISSUER_URL` | URL pública de Keycloak (para validar tokens) | — |
| `AWS_ACCESS_KEY_ID` | Access key de AWS | — |
| `AWS_SECRET_ACCESS_KEY` | Secret key de AWS | — |
| `AWS_S3_BUCKET_NAME` | Nombre del bucket S3 | — |
| `AWS_S3_REGION` | Región de AWS | `sa-east-1` |
