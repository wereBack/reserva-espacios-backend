"""
Rutas REST para gestión de reservas.
"""

from flask import Blueprint, jsonify, request
from reservas.service import ReservaService

reservas_bp = Blueprint('reservas', __name__, url_prefix='/api/reservas')


@reservas_bp.route('', methods=['POST'])
def create_reservation():
    """
    Crear una nueva reserva temporal.
    
    Request Body:
        {
            "space_id": "uuid-del-espacio",
            "user_id": "id-usuario-keycloak" (opcional),
            "asignee": "nombre-asignado" (opcional),
            "ttl_seconds": 300 (opcional, default de config)
        }
        
    Returns:
        201: Reserva creada exitosamente
        400: Datos inválidos o espacio no disponible
        500: Error interno
    """
    try:
        data = request.get_json()
        
        if not data or 'space_id' not in data:
            return jsonify({
                'error': 'space_id es requerido',
                'status': 'error'
            }), 400
        
        reserva, error = ReservaService.create_reservation(
            space_id=data['space_id'],
            user_id=data.get('user_id'),
            asignee=data.get('asignee'),
            ttl_seconds=data.get('ttl_seconds'),
        )
        
        if error:
            return jsonify({
                'error': error,
                'status': 'error'
            }), 400
        
        return jsonify({
            'status': 'success',
            'message': 'Reserva creada exitosamente',
            'reservation': reserva.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/<reservation_id>', methods=['GET'])
def get_reservation(reservation_id):
    """
    Obtener una reserva por ID.
    
    Args:
        reservation_id: UUID de la reserva
        
    Returns:
        200: Reserva encontrada
        404: Reserva no encontrada
    """
    try:
        reserva = ReservaService.get_reservation_by_id(reservation_id)
        
        if not reserva:
            return jsonify({
                'error': 'Reserva no encontrada',
                'status': 'error'
            }), 404
        
        return jsonify({
            'status': 'success',
            'reservation': reserva.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/<reservation_id>/status', methods=['GET'])
def get_reservation_status(reservation_id):
    """
    Obtener estado detallado de una reserva (BD + Redis + TTL).
    
    Args:
        reservation_id: UUID de la reserva
        
    Returns:
        200: Estado de la reserva
        {
            "exists_in_database": true,
            "is_active_in_redis": true,
            "ttl_seconds": 250,
            "reservation": {...}
        }
    """
    try:
        status = ReservaService.get_reservation_status(reservation_id)
        
        if status is None:
            return jsonify({
                'error': 'Error obteniendo estado de la reserva',
                'status': 'error'
            }), 500
        
        return jsonify({
            'status': 'success',
            **status
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/<reservation_id>', methods=['DELETE'])
def cancel_reservation(reservation_id):
    """
    Cancelar una reserva activa.
    
    Args:
        reservation_id: UUID de la reserva
        
    Returns:
        200: Reserva cancelada
        400: Reserva no puede ser cancelada
        404: Reserva no encontrada
    """
    try:
        reserva, error = ReservaService.cancel_reservation(reservation_id)
        
        if error:
            status_code = 404 if 'no encontrada' in error.lower() else 400
            return jsonify({
                'error': error,
                'status': 'error'
            }), status_code
        
        return jsonify({
            'status': 'success',
            'message': 'Reserva cancelada exitosamente',
            'reservation': reserva.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/<reservation_id>/refresh', methods=['POST'])
def refresh_reservation_ttl(reservation_id):
    """
    Renovar el TTL de una reserva activa.
    
    Request Body (opcional):
        {
            "ttl_seconds": 300
        }
        
    Args:
        reservation_id: UUID de la reserva
        
    Returns:
        200: TTL renovado
        400: No se puede renovar
        404: Reserva no encontrada
    """
    try:
        data = request.get_json() or {}
        
        reserva, error = ReservaService.refresh_reservation_ttl(
            reservation_id,
            ttl_seconds=data.get('ttl_seconds'),
        )
        
        if error:
            status_code = 404 if 'no encontrada' in error.lower() else 400
            return jsonify({
                'error': error,
                'status': 'error'
            }), status_code
        
        return jsonify({
            'status': 'success',
            'message': 'TTL renovado exitosamente',
            'reservation': reserva.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/space/<space_id>', methods=['GET'])
def get_reservations_by_space(space_id):
    """
    Obtener todas las reservas de un espacio.
    
    Args:
        space_id: UUID del espacio
        
    Returns:
        200: Lista de reservas
    """
    try:
        reservas = ReservaService.get_reservations_by_space(space_id)
        
        return jsonify({
            'status': 'success',
            'reservations': [r.to_dict() for r in reservas]
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/space/<space_id>/active', methods=['GET'])
def get_active_reservation_by_space(space_id):
    """
    Obtener la reserva activa de un espacio si existe.
    
    Args:
        space_id: UUID del espacio
        
    Returns:
        200: Reserva activa o null
    """
    try:
        reserva = ReservaService.get_active_reservation_by_space(space_id)
        
        return jsonify({
            'status': 'success',
            'reservation': reserva.to_dict() if reserva else None
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


# ==================== ENDPOINTS ADMIN ====================

@reservas_bp.route('/pending', methods=['GET'])
def get_pending_reservations():
    """
    Obtener todas las reservas pendientes de confirmación.
    Para uso del panel de admin.
    
    Returns:
        200: Lista de reservas pendientes
    """
    try:
        reservas = ReservaService.get_pending_reservations()
        
        return jsonify({
            'status': 'success',
            'reservations': [r.to_dict() for r in reservas]
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/<reservation_id>/confirm', methods=['POST'])
def confirm_reservation(reservation_id):
    """
    Confirmar una reserva pendiente (PENDING -> RESERVED).
    Solo para admin.
    
    Args:
        reservation_id: UUID de la reserva
        
    Returns:
        200: Reserva confirmada
        400: No se puede confirmar
        404: Reserva no encontrada
    """
    try:
        reserva, error = ReservaService.confirm_reservation(reservation_id)
        
        if error:
            status_code = 404 if 'no encontrada' in error.lower() else 400
            return jsonify({
                'error': error,
                'status': 'error'
            }), status_code
        
        return jsonify({
            'status': 'success',
            'message': 'Reserva confirmada exitosamente',
            'reservation': reserva.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/<reservation_id>/reject', methods=['POST'])
def reject_reservation(reservation_id):
    """
    Rechazar una reserva pendiente (PENDING -> CANCELLED).
    Solo para admin.
    
    Args:
        reservation_id: UUID de la reserva
        
    Returns:
        200: Reserva rechazada
        400: No se puede rechazar
        404: Reserva no encontrada
    """
    try:
        reserva, error = ReservaService.reject_reservation(reservation_id)
        
        if error:
            status_code = 404 if 'no encontrada' in error.lower() else 400
            return jsonify({
                'error': error,
                'status': 'error'
            }), status_code
        
        return jsonify({
            'status': 'success',
            'message': 'Reserva rechazada',
            'reservation': reserva.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

