"""
Rutas REST para gestión de reservas.
"""

from flask import Blueprint, jsonify, request
from database import db
from reservas.service import ReservaService
from auth import require_auth, require_role, get_current_user

reservas_bp = Blueprint('reservas', __name__, url_prefix='/api/reservas')


@reservas_bp.route('', methods=['POST'])
@require_auth
def create_reservation():
    """
    Crear una nueva reserva temporal. Requiere autenticacion y perfil completo.
    
    Request Body:
        {
            "space_id": "uuid-del-espacio",
            "asignee": "nombre-asignado" (opcional),
            "ttl_seconds": 300 (opcional, default de config)
        }
        
    Returns:
        201: Reserva creada exitosamente
        400: Datos inválidos o espacio no disponible
        403: Perfil incompleto
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
        
        if not user_id:
            return jsonify({
                'error': 'Usuario no identificado',
                'status': 'error'
            }), 401
        
        # Verificar que el perfil esté completo
        from user_profiles.models.user_profile import UserProfile
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        if not profile or not profile.is_complete():
            return jsonify({
                'error': 'Debes completar tu perfil antes de hacer una reserva',
                'status': 'error',
                'code': 'PROFILE_INCOMPLETE'
            }), 403
        
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


# ==================== ENDPOINTS USUARIO ====================

@reservas_bp.route('/mis-reservas', methods=['GET'])
@require_auth
def get_my_reservations():
    """
    Obtener todas las reservas del usuario autenticado.
    
    Returns:
        200: Lista de reservas del usuario
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') if current_user else None
        
        if not user_id:
            return jsonify({
                'error': 'Usuario no identificado',
                'status': 'error'
            }), 401
        
        reservas = ReservaService.get_reservations_by_user(user_id)
        
        return jsonify({
            'status': 'success',
            'reservations': [r.to_dict() for r in reservas]
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/<reservation_id>/solicitar-cancelacion', methods=['POST'])
@require_auth
def request_cancellation(reservation_id):
    """
    Solicitar cancelación de una reserva.
    - Si está PENDING: se cancela directamente
    - Si está RESERVED: queda en estado CANCELLATION_REQUESTED para revisión del admin
    
    Args:
        reservation_id: UUID de la reserva
        
    Returns:
        200: Solicitud procesada
        400: No se puede procesar
        404: Reserva no encontrada
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') if current_user else None
        
        if not user_id:
            return jsonify({
                'error': 'Usuario no identificado',
                'status': 'error'
            }), 401
        
        reserva, error = ReservaService.request_cancellation(reservation_id, user_id)
        
        if error:
            status_code = 404 if 'no encontrada' in error.lower() else 400
            return jsonify({
                'error': error,
                'status': 'error'
            }), status_code
        
        message = 'Reserva cancelada' if reserva.estado == 'CANCELLED' else 'Solicitud de cancelación enviada al administrador'
        
        return jsonify({
            'status': 'success',
            'message': message,
            'reservation': reserva.to_dict()
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
    Al confirmar, actualiza el nombre del espacio al nombre de la empresa o del cliente.
    
    Args:
        reservation_id: UUID de la reserva
        
    Returns:
        200: Reserva confirmada
        400: No se puede confirmar
        404: Reserva no encontrada
    """
    try:
        from spaces.models.space import Space
        from user_profiles.models.user_profile import UserProfile
        
        reserva, error = ReservaService.confirm_reservation(reservation_id)
        
        if error:
            status_code = 404 if 'no encontrada' in error.lower() else 400
            return jsonify({
                'error': error,
                'status': 'error'
            }), status_code
        
        # Actualizar el nombre del espacio al nombre de la empresa o del cliente
        space = Space.query.get(reserva.espacio_id)
        updated_space_name = None
        if space and reserva.user_id:
            profile = UserProfile.query.filter_by(user_id=reserva.user_id).first()
            new_name = None
            
            # Prioridad: empresa > asignee de la reserva
            if profile and profile.company and profile.company.strip():
                new_name = profile.company.strip()
            elif reserva.asignee:
                new_name = reserva.asignee
            
            if new_name:
                space.name = new_name
                updated_space_name = new_name
                db.session.commit()
        
        response_data = {
            'status': 'success',
            'message': 'Reserva confirmada exitosamente',
            'reservation': reserva.to_dict()
        }
        
        # Incluir el nombre actualizado del space si cambió
        if updated_space_name:
            response_data['updated_space_name'] = updated_space_name
        
        return jsonify(response_data), 200
        
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


@reservas_bp.route('/cancellation-requests', methods=['GET'])
@require_auth
@require_role('Admin')
def get_cancellation_requests():
    """
    Obtener todas las solicitudes de cancelación pendientes. Solo Admin.
    
    Returns:
        200: Lista de reservas con solicitud de cancelación
    """
    try:
        from reservas.models.reserva import Reserva
        reservas = Reserva.query.filter_by(estado='CANCELLATION_REQUESTED').all()
        
        return jsonify({
            'status': 'success',
            'reservations': [r.to_dict() for r in reservas]
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/<reservation_id>/approve-cancellation', methods=['POST'])
@require_auth
@require_role('Admin')
def approve_cancellation(reservation_id):
    """
    Aprobar una solicitud de cancelación (CANCELLATION_REQUESTED -> CANCELLED). Solo Admin.
    
    Args:
        reservation_id: UUID de la reserva
        
    Returns:
        200: Cancelación aprobada
        400: No se puede aprobar
        404: Reserva no encontrada
    """
    try:
        from reservas.models.reserva import Reserva
        from spaces.models.space import Space
        from websocket.socket_manager import emit_reservation_cancelled
        
        reserva = Reserva.query.get(reservation_id)
        if not reserva:
            return jsonify({
                'error': 'Reserva no encontrada',
                'status': 'error'
            }), 404
        
        if reserva.estado != 'CANCELLATION_REQUESTED':
            return jsonify({
                'error': f'La reserva no tiene solicitud de cancelación pendiente (estado: {reserva.estado})',
                'status': 'error'
            }), 400
        
        reserva.estado = 'CANCELLED'
        db.session.commit()
        
        # Obtener plano_id para el WebSocket
        space = Space.query.get(reserva.espacio_id)
        plano_id = str(space.plano_id) if space and space.plano_id else None
        
        emit_reservation_cancelled(reserva.to_dict(), plano_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Cancelación aprobada',
            'reservation': reserva.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@reservas_bp.route('/<reservation_id>/reject-cancellation', methods=['POST'])
@require_auth
@require_role('Admin')
def reject_cancellation(reservation_id):
    """
    Rechazar una solicitud de cancelación (CANCELLATION_REQUESTED -> RESERVED). Solo Admin.
    
    Args:
        reservation_id: UUID de la reserva
        
    Returns:
        200: Solicitud rechazada, reserva mantiene estado RESERVED
        400: No se puede rechazar
        404: Reserva no encontrada
    """
    try:
        from reservas.models.reserva import Reserva
        from spaces.models.space import Space
        from websocket.socket_manager import emit_reservation_updated
        
        reserva = Reserva.query.get(reservation_id)
        if not reserva:
            return jsonify({
                'error': 'Reserva no encontrada',
                'status': 'error'
            }), 404
        
        if reserva.estado != 'CANCELLATION_REQUESTED':
            return jsonify({
                'error': f'La reserva no tiene solicitud de cancelación pendiente (estado: {reserva.estado})',
                'status': 'error'
            }), 400
        
        reserva.estado = 'RESERVED'
        db.session.commit()
        
        # Obtener plano_id para el WebSocket
        space = Space.query.get(reserva.espacio_id)
        plano_id = str(space.plano_id) if space and space.plano_id else None
        
        emit_reservation_updated(reserva.to_dict(), plano_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Solicitud de cancelación rechazada, la reserva permanece activa',
            'reservation': reserva.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

