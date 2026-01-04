"""
Servicio para subir archivos a AWS S3.
Usa multiprocessing para evitar conflictos con eventlet.
"""
import uuid
import multiprocessing
from config import settings


def _upload_to_s3_process(file_bytes: bytes, unique_filename: str, content_type: str, 
                          bucket_name: str, region: str, access_key: str, secret_key: str,
                          result_queue):
    """
    Funcion que se ejecuta en un proceso separado para subir a S3.
    Recibe la configuracion como parametros para evitar importar settings en el proceso hijo.
    """
    try:
        import boto3
        from io import BytesIO
        from botocore.exceptions import ClientError
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        file_obj = BytesIO(file_bytes)
        
        s3_client.upload_fileobj(
            file_obj,
            bucket_name,
            unique_filename,
            ExtraArgs=extra_args
        )
        
        # Construir URL publica
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{unique_filename}"
        result_queue.put(('success', url))
        
    except Exception as e:
        result_queue.put(('error', str(e)))


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
    
    # Crear cola para recibir resultado del proceso
    result_queue = multiprocessing.Queue()
    
    # Crear y ejecutar proceso
    process = multiprocessing.Process(
        target=_upload_to_s3_process,
        args=(
            file_bytes, 
            unique_filename, 
            content_type,
            settings.AWS_S3_BUCKET_NAME,
            settings.AWS_S3_REGION,
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY,
            result_queue
        )
    )
    
    process.start()
    process.join(timeout=60)  # Esperar maximo 60 segundos
    
    if process.is_alive():
        process.terminate()
        raise Exception("Timeout al subir archivo a S3")
    
    # Obtener resultado
    if result_queue.empty():
        raise Exception("No se recibio respuesta del proceso de subida")
    
    status, result = result_queue.get()
    
    if status == 'error':
        raise Exception(f"Error al subir archivo a S3: {result}")
    
    return result
