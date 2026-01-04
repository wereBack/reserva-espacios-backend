"""
Listener para eventos de expiración de claves en Redis.
"""

import logging
import threading
from typing import Callable, Optional

from redis_client.client import get_redis_client
from redis_client.service import RedisService

logger = logging.getLogger(__name__)


class RedisExpirationListener:
    """
    Listener que escucha eventos de expiración de claves Redis.
    Ejecuta un callback cuando una reserva expira.
    """
    
    def __init__(self, callback: Callable[[str], None]):
        """
        Inicializa el listener.
        
        Args:
            callback: Función a ejecutar cuando una reserva expira.
                      Recibe el ID de la reserva como argumento.
        """
        self._callback = callback
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._pubsub = None
    
    def start(self):
        """Inicia el listener en un thread separado."""
        if self._running:
            logger.warning("El listener ya está corriendo")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info("Redis expiration listener iniciado")
    
    def stop(self):
        """Detiene el listener."""
        self._running = False
        
        if self._pubsub:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.close()
            except Exception as e:
                logger.error(f"Error cerrando pubsub: {e}")
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        
        logger.info("Redis expiration listener detenido")
    
    def _listen(self):
        """
        Escucha eventos de expiración en Redis.
        Se suscribe al canal __keyevent@0__:expired.
        """
        try:
            client = get_redis_client()
            self._pubsub = client.pubsub()
            
            # Suscribirse a eventos de expiración
            # Requiere que Redis tenga configurado: notify-keyspace-events Ex
            self._pubsub.subscribe('__keyevent@0__:expired')
            
            logger.info("Suscrito a eventos de expiración de Redis")
            
            for message in self._pubsub.listen():
                if not self._running:
                    break
                
                if message['type'] == 'message':
                    expired_key = message['data']
                    self._handle_expiration(expired_key)
                    
        except Exception as e:
            logger.error(f"Error en el listener de expiración: {e}")
            self._running = False
    
    def _handle_expiration(self, expired_key: str):
        """
        Maneja la expiración de una clave.
        
        Args:
            expired_key: Clave que expiró
        """
        try:
            # Verificar que sea una clave de reserva
            if not expired_key.startswith(RedisService.RESERVATION_PREFIX):
                return
            
            # Extraer el ID de la reserva
            reservation_id = expired_key.replace(RedisService.RESERVATION_PREFIX, '')
            
            logger.info(f"Reserva expirada detectada: {reservation_id}")
            
            # Ejecutar callback
            self._callback(reservation_id)
            
        except Exception as e:
            logger.error(f"Error procesando expiración de {expired_key}: {e}")

