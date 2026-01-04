"""
Cliente Redis singleton para la aplicación.
"""

import redis
from config import settings


class RedisClient:
    """
    Singleton para el cliente Redis.
    Gestiona una única conexión a Redis para toda la aplicación.
    """
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self) -> redis.Redis:
        """
        Obtiene el cliente Redis, creándolo si no existe.
        
        Returns:
            redis.Redis: Cliente Redis configurado
        """
        if self._client is None:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
            )
        return self._client
    
    def close(self):
        """Cierra la conexión a Redis."""
        if self._client is not None:
            self._client.close()
            self._client = None


# Instancia global del cliente
redis_client = RedisClient()


def get_redis_client() -> redis.Redis:
    """
    Función helper para obtener el cliente Redis.
    
    Returns:
        redis.Redis: Cliente Redis configurado
    """
    return redis_client.get_client()

