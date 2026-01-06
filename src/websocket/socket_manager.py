"""
Gestión de WebSocket con Flask-SocketIO.
"""

from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from auth.keycloak import token_validator

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
        logger=False,
        engineio_logger=False,
    )
    
    # Registrar handlers de eventos
    _register_handlers()
    
    return socketio


def _validate_token_from_request() -> tuple[dict | None, str | None]:
    """
    Extrae y valida el token JWT de la conexión WebSocket.
    El token puede venir como query param 'token' o en el header Authorization.
    
    Returns:
        Tuple de (claims del usuario, None) si el token es valido
        Tuple de (None, None) si no hay token (cliente publico)
        Tuple de (None, error) si el token es invalido
    """
    # Intentar obtener token de query params
    token = request.args.get('token')
    
    # Si no está en query params, intentar del header Authorization
    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
    
    # Si no hay token, permitir como cliente publico
    if not token:
        return None, None
    
    # Si hay token, validarlo
    claims, error = token_validator.validate_token(token)
    if error:
        return None, error
    
    return claims, None


def _register_handlers():
    """Registra los handlers de eventos WebSocket."""
    
    @socketio.on('connect', namespace='/reservas')
    def handle_connect():
        """
        Maneja la conexión de un cliente.
        - Si se envía token: lo valida y rechaza si es inválido
        - Si no hay token: permite conexión como cliente público
        """
        claims, error = _validate_token_from_request()
        
        # Si hay error de validación (token inválido), rechazar
        if error:
            emit('auth_error', {'error': error})
            disconnect()
            return False
        
        # Conexión exitosa (autenticada o pública)
        if claims:
            # Usuario autenticado
            emit('connected', {
                'status': 'ok',
                'message': 'Conectado al sistema de reservas',
                'authenticated': True,
                'user': claims.get('preferred_username')
            })
        else:
            # Cliente público (sin autenticación)
            emit('connected', {
                'status': 'ok',
                'message': 'Conectado al sistema de reservas (modo público)',
                'authenticated': False
            })
    
    @socketio.on('disconnect', namespace='/reservas')
    def handle_disconnect():
        """Maneja la desconexión de un cliente."""
        pass
    
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


def emit_space_updated(space_data: dict, plano_id: str = None):
    """
    Emite un evento cuando se actualiza un espacio (stand).
    Siempre emite a todos los clientes conectados (broadcast).
    
    Args:
        space_data: Datos del espacio actualizado
        plano_id: ID del plano (incluido en el payload para filtrar en frontend)
    """
    event_data = {
        'event': 'space_updated',
        'space': space_data,
        'plano_id': plano_id
    }
    
    # Broadcast a todos los clientes conectados al namespace
    socketio.emit('space_updated', event_data, namespace='/reservas')
