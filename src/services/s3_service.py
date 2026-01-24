"""
Servicio para subir y obtener archivos de AWS S3.
"""

import uuid
from io import BytesIO

import boto3
from botocore.exceptions import ClientError

from config import settings


def get_s3_client():
    """Obtiene un cliente S3 configurado."""
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
    )


def get_file(s3_key: str) -> tuple[bytes | None, str | None, str | None]:
    """
    Descarga un archivo de S3.

    Args:
        s3_key: Clave del archivo en S3 (ej: "planos/uuid.svg")

    Returns:
        Tuple de (bytes del archivo, content_type, error_message)
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=s3_key)
        file_bytes = response["Body"].read()
        content_type = response.get("ContentType", "application/octet-stream")
        return file_bytes, content_type, None
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None, None, "Archivo no encontrado"
        return None, None, f"Error al obtener archivo: {e}"
    except Exception as e:
        return None, None, f"Error inesperado: {e}"


def upload_file(file_data, original_filename: str, content_type: str = None) -> str:
    """
    Sube un archivo a S3 y retorna la URL publica.

    Args:
        file_data: Objeto file-like con los datos del archivo
        original_filename: Nombre original del archivo (para extraer extension)
        content_type: Tipo MIME del archivo (opcional)

    Returns:
        URL publica del archivo subido

    Raises:
        Exception: Si hay error al subir el archivo
    """
    # Generar nombre unico para evitar colisiones
    extension = original_filename.rsplit(".", 1)[-1] if "." in original_filename else ""
    unique_filename = f"planos/{uuid.uuid4()}.{extension}" if extension else f"planos/{uuid.uuid4()}"

    # Leer los bytes del archivo
    file_bytes = file_data.read()

    try:
        s3_client = get_s3_client()

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        file_obj = BytesIO(file_bytes)

        s3_client.upload_fileobj(file_obj, settings.AWS_S3_BUCKET_NAME, unique_filename, ExtraArgs=extra_args)

        # Construir URL publica
        url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_S3_REGION}.amazonaws.com/{unique_filename}"
        return url

    except ClientError as e:
        raise Exception(f"Error al subir archivo a S3: {e}")
    except Exception as e:
        raise Exception(f"Error inesperado al subir archivo: {e}")
