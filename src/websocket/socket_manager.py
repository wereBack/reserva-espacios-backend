"""
Gestión de WebSocket con Flask-SocketIO.
"""

import logging
from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room

logger = logging.getLogger(__name__)

# Instancia global de SocketIO
socketio = SocketIO()


def init_socketio(app: Flask) -> SocketIO:
    """
    Inicializa Flask-SocketIO con la aplicación Flask.
    
    Args:
        app: Aplicación Flask
        
    Returns:
        SocketIO: Instancia configurada de SocketIO
    """
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode='gevent',
        logger=True,
        engineio_logger=True if app.debug else False,
    )
    
    # Registrar handlers de eventos
    _register_handlers()
    
    logger.info("Flask-SocketIO inicializado")
    return socketio


def _register_handlers():
    """Registra los handlers de eventos WebSocket."""
    
    @socketio.on('connect', namespace='/reservas')
    def handle_connect():
        """Maneja la conexión de un cliente."""
        logger.info("Cliente conectado al namespace /reservas")
        emit('connected', {'status': 'ok', 'message': 'Conectado al sistema de reservas'})
    
    @socketio.on('disconnect', namespace='/reservas')
    def handle_disconnect():
        """Maneja la desconexión de un cliente."""
        logger.info("Cliente desconectado del namespace /reservas")
    
    @socketio.on('join_plano', namespace='/reservas')
    def handle_join_plano(data):
        """
        Permite a un cliente unirse a una sala específica de un plano.
        Así solo recibirá eventos de ese plano.
        
        Args:
            data: {'plano_id': 'uuid-del-plano'}
        """
        plano_id = data.get('plano_id')
        if plano_id:
            join_room(f'plano_{plano_id}')
            logger.info(f"Cliente unido a sala plano_{plano_id}")
            emit('joined_plano', {'plano_id': plano_id, 'status': 'ok'})
    
    @socketio.on('leave_plano', namespace='/reservas')
    def handle_leave_plano(data):
        """
        Permite a un cliente salir de una sala de plano.
        
        Args:
            data: {'plano_id': 'uuid-del-plano'}
        """
        plano_id = data.get('plano_id')
        if plano_id:
            leave_room(f'plano_{plano_id}')
            logger.info(f"Cliente salió de sala plano_{plano_id}")
            emit('left_plano', {'plano_id': plano_id, 'status': 'ok'})


# Funciones para emitir eventos desde otros módulos

def emit_reservation_created(reservation_data: dict, plano_id: str = None):
    """
    Emite un evento cuando se crea una reserva.
    Siempre emite a todos los clientes conectados (broadcast).
    
    Args:
        reservation_data: Datos de la reserva creada
        plano_id: ID del plano (incluido en el payload para filtrar en frontend)
    """
    event_data = {
        'event': 'reservation_created',
        'reservation': reservation_data,
        'plano_id': plano_id
    }
    
    # Broadcast a todos los clientes conectados al namespace
    socketio.emit('reservation_created', event_data, namespace='/reservas')
    
    logger.info(f"Evento reservation_created emitido (broadcast) para reserva {reservation_data.get('id')}")


def emit_reservation_updated(reservation_data: dict, plano_id: str = None):
    """
    Emite un evento cuando se actualiza una reserva.
    Siempre emite a todos los clientes conectados (broadcast).
    
    Args:
        reservation_data: Datos de la reserva actualizada
        plano_id: ID del plano (incluido en el payload para filtrar en frontend)
    """
    event_data = {
        'event': 'reservation_updated',
        'reservation': reservation_data,
        'plano_id': plano_id
    }
    
    # Broadcast a todos los clientes conectados al namespace
    socketio.emit('reservation_updated', event_data, namespace='/reservas')
    
    logger.info(f"Evento reservation_updated emitido (broadcast) para reserva {reservation_data.get('id')}")


def emit_reservation_expired(reservation_data: dict, plano_id: str = None):
    """
    Emite un evento cuando una reserva expira.
    Siempre emite a todos los clientes conectados (broadcast).
    
    Args:
        reservation_data: Datos de la reserva expirada
        plano_id: ID del plano (incluido en el payload para filtrar en frontend)
    """
    event_data = {
        'event': 'reservation_expired',
        'reservation': reservation_data,
        'plano_id': plano_id
    }
    
    # Broadcast a todos los clientes conectados al namespace
    socketio.emit('reservation_expired', event_data, namespace='/reservas')
    
    logger.info(f"Evento reservation_expired emitido (broadcast) para reserva {reservation_data.get('id')}")


def emit_reservation_cancelled(reservation_data: dict, plano_id: str = None):
    """
    Emite un evento cuando se cancela una reserva.
    Siempre emite a todos los clientes conectados (broadcast).
    
    Args:
        reservation_data: Datos de la reserva cancelada
        plano_id: ID del plano (incluido en el payload para filtrar en frontend)
    """
    event_data = {
        'event': 'reservation_cancelled',
        'reservation': reservation_data,
        'plano_id': plano_id
    }
    
    # Broadcast a todos los clientes conectados al namespace
    socketio.emit('reservation_cancelled', event_data, namespace='/reservas')
    
    logger.info(f"Evento reservation_cancelled emitido (broadcast) para reserva {reservation_data.get('id')}")

