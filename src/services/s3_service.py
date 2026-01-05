"""
Servicio para subir archivos a AWS S3.
"""
import uuid
from io import BytesIO
import boto3
from botocore.exceptions import ClientError
from config import settings


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
    extension = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
    unique_filename = f"planos/{uuid.uuid4()}.{extension}" if extension else f"planos/{uuid.uuid4()}"
    
    # Leer los bytes del archivo
    file_bytes = file_data.read()
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION
        )
        
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        file_obj = BytesIO(file_bytes)
        
        s3_client.upload_fileobj(
            file_obj,
            settings.AWS_S3_BUCKET_NAME,
            unique_filename,
            ExtraArgs=extra_args
        )
        
        # Construir URL publica
        url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_S3_REGION}.amazonaws.com/{unique_filename}"
        return url
        
    except ClientError as e:
        raise Exception(f"Error al subir archivo a S3: {e}")
    except Exception as e:
        raise Exception(f"Error inesperado al subir archivo: {e}")
