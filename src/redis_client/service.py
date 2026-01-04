"""
Servicio Redis para operaciones CRUD con TTL.
"""

import json
import logging
from typing import Optional, Any

from redis_client.client import get_redis_client
from config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    Servicio para operaciones Redis con reservas.
    Maneja el almacenamiento temporal con TTL automático.
    """
    
    # Prefijo para las claves de reservas
    RESERVATION_PREFIX = "reservation:"
    
    @classmethod
    def _get_key(cls, reservation_id: str) -> str:
        """
        Genera la clave Redis para una reserva.
        
        Args:
            reservation_id: ID de la reserva
            
        Returns:
            str: Clave con prefijo
        """
        return f"{cls.RESERVATION_PREFIX}{reservation_id}"
    
    @classmethod
    def set_reservation(
        cls,
        reservation_id: str,
        data: dict,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Guarda una reserva en Redis con TTL.
        
        Args:
            reservation_id: ID de la reserva
            data: Datos de la reserva a almacenar
            ttl_seconds: TTL en segundos (usa config por defecto si no se especifica)
            
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            client = get_redis_client()
            key = cls._get_key(reservation_id)
            ttl = ttl_seconds or settings.RESERVATION_TTL_SECONDS
            
            # Serializar datos a JSON
            value = json.dumps(data)
            
            # Guardar con TTL
            client.setex(key, ttl, value)
            
            logger.info(f"Reserva {reservation_id} guardada en Redis con TTL={ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando reserva {reservation_id} en Redis: {e}")
            return False
    
    @classmethod
    def get_reservation(cls, reservation_id: str) -> Optional[dict]:
        """
        Obtiene una reserva de Redis.
        
        Args:
            reservation_id: ID de la reserva
            
        Returns:
            dict: Datos de la reserva o None si no existe
        """
        try:
            client = get_redis_client()
            key = cls._get_key(reservation_id)
            
            value = client.get(key)
            if value is None:
                return None
            
            return json.loads(value)
            
        except Exception as e:
            logger.error(f"Error obteniendo reserva {reservation_id} de Redis: {e}")
            return None
    
    @classmethod
    def delete_reservation(cls, reservation_id: str) -> bool:
        """
        Elimina una reserva de Redis.
        
        Args:
            reservation_id: ID de la reserva
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            client = get_redis_client()
            key = cls._get_key(reservation_id)
            
            deleted = client.delete(key)
            
            if deleted:
                logger.info(f"Reserva {reservation_id} eliminada de Redis")
            
            return deleted > 0
            
        except Exception as e:
            logger.error(f"Error eliminando reserva {reservation_id} de Redis: {e}")
            return False
    
    @classmethod
    def get_ttl(cls, reservation_id: str) -> int:
        """
        Obtiene el TTL restante de una reserva.
        
        Args:
            reservation_id: ID de la reserva
            
        Returns:
            int: Segundos restantes, -1 si no tiene TTL, -2 si no existe
        """
        try:
            client = get_redis_client()
            key = cls._get_key(reservation_id)
            
            return client.ttl(key)
            
        except Exception as e:
            logger.error(f"Error obteniendo TTL de reserva {reservation_id}: {e}")
            return -2
    
    @classmethod
    def exists(cls, reservation_id: str) -> bool:
        """
        Verifica si una reserva existe en Redis.
        
        Args:
            reservation_id: ID de la reserva
            
        Returns:
            bool: True si existe
        """
        try:
            client = get_redis_client()
            key = cls._get_key(reservation_id)
            
            return client.exists(key) > 0
            
        except Exception as e:
            logger.error(f"Error verificando existencia de reserva {reservation_id}: {e}")
            return False
    
    @classmethod
    def refresh_ttl(cls, reservation_id: str, ttl_seconds: Optional[int] = None) -> bool:
        """
        Renueva el TTL de una reserva existente.
        
        Args:
            reservation_id: ID de la reserva
            ttl_seconds: Nuevo TTL en segundos
            
        Returns:
            bool: True si se renovó correctamente
        """
        try:
            client = get_redis_client()
            key = cls._get_key(reservation_id)
            ttl = ttl_seconds or settings.RESERVATION_TTL_SECONDS
            
            result = client.expire(key, ttl)
            
            if result:
                logger.info(f"TTL de reserva {reservation_id} renovado a {ttl}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error renovando TTL de reserva {reservation_id}: {e}")
            return False


