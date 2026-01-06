"""
Rutas REST para gestión de reservas.
"""

from flask import Blueprint, jsonify, request
from reservas.service import ReservaService
from auth import require_auth, require_role, get_current_user

reservas_bp = Blueprint('reservas', __name__, url_prefix='/api/reservas')


@reservas_bp.route('', methods=['POST'])
@require_auth
def create_reservation():
    """
    Crear una nueva reserva temporal. Requiere autenticacion.
    
    Request Body:
        {
            "space_id": "uuid-del-espacio",
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
        
        # Obtener usuario autenticado
        current_user = get_current_user()
        user_id = current_user.get('id') if current_user else None
        asignee = data.get('asignee') or (current_user.get('name') if current_user else None)
        
        reserva, error = ReservaService.create_reservation(
            space_id=data['space_id'],
            user_id=user_id,
            asignee=asignee,
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


@reservas_bp.route('/<reservation_id>', methods=['DELETE'])
@require_auth
def cancel_reservation(reservation_id):
    """
    Cancelar una reserva activa. Requiere autenticacion.
    
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
@require_auth
@require_role('Admin')
def get_pending_reservations():
    """
    Obtener todas las reservas pendientes de confirmación. Solo Admin.
    
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
@require_auth
@require_role('Admin')
def confirm_reservation(reservation_id):
    """
    Confirmar una reserva pendiente (PENDING -> RESERVED). Solo Admin.
    
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
@require_auth
@require_role('Admin')
def reject_reservation(reservation_id):
    """
    Rechazar una reserva pendiente (PENDING -> CANCELLED). Solo Admin.
    
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

