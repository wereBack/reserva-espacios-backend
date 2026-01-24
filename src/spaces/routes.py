"""
Endpoints para gestión de espacios (stands) y reservas.
"""

from flask import Blueprint, jsonify, request

from auth import get_current_user, require_auth, require_role
from database import db
from reservas.models.reserva import Reserva
from reservas.service import ReservaService
from spaces.models.space import Space
from spaces.models.zone import Zone
from websocket.socket_manager import emit_reservation_cancelled, emit_space_updated

# Blueprint para endpoints de espacios
spaces_bp = Blueprint("spaces", __name__, url_prefix="/spaces")


@spaces_bp.route("/", methods=["GET"])
def get_spaces():
    """Listar todos los espacios."""
    spaces = Space.query.all()
    return jsonify([space.to_dict() for space in spaces]), 200


@spaces_bp.route("/", methods=["POST"])
@require_auth
@require_role("Admin")
def create_space():
    """Crear un nuevo espacio (stand) individual. Solo Admin."""
    data = request.json or {}

    # Validar que tenga plano_id
    plano_id = data.get("plano_id")
    if not plano_id:
        return jsonify({"error": "plano_id es requerido", "status": "error"}), 400

    try:
        new_space = Space(
            kind=data.get("kind", "rect"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 100),
            height=data.get("height", 100),
            color=data.get("color", "#3b82f6"),
            price=data.get("price"),
            name=data.get("name", "Nuevo Stand"),
            plano_id=plano_id,
            zone_id=data.get("zone_id"),
            active=data.get("active", True),
        )
        db.session.add(new_space)
        db.session.commit()

        # Emitir evento WebSocket
        emit_space_updated(new_space.to_dict(), plano_id)

        return jsonify(new_space.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


@spaces_bp.route("/<string:space_id>", methods=["GET"])
def get_space(space_id):
    """Obtener un espacio por ID."""
    space = Space.query.get(space_id)
    if not space:
        return jsonify({"error": "Espacio no encontrado", "status": "error"}), 404
    return jsonify(space.to_dict()), 200


@spaces_bp.route("/<string:space_id>", methods=["PATCH"])
@require_auth
@require_role("Admin")
def update_space(space_id):
    """Actualizar un espacio (nombre, precio, estado, etc). Solo Admin."""
    space = Space.query.get(space_id)
    if not space:
        return jsonify({"error": "Espacio no encontrado", "status": "error"}), 404

    data = request.json or {}

    try:
        if "name" in data:
            space.name = data["name"]
        if "price" in data:
            space.price = data["price"]
        if "active" in data:
            space.active = data["active"]
        # Position and size fields
        if "x" in data:
            space.x = data["x"]
        if "y" in data:
            space.y = data["y"]
        if "width" in data:
            space.width = data["width"]
        if "height" in data:
            space.height = data["height"]
        if "color" in data:
            space.color = data["color"]
        if "rotation" in data:
            space.rotation = data["rotation"]
        # Zone association
        if "zone_id" in data:
            space.zone_id = data["zone_id"]

        # Procesar cambio de estado (status)
        if "status" in data:
            status = data["status"]
            if status == "BLOCKED":
                # Bloquear el stand
                space.active = False
                # Cancelar reservaciones activas
                for reserva in space.reservations:
                    if reserva.estado in ["PENDING", "RESERVED"]:
                        reserva.estado = "CANCELLED"
            elif status == "AVAILABLE":
                # Desbloquear el stand
                space.active = True
                # Cancelar reservaciones activas para dejarlo disponible
                for reserva in space.reservations:
                    if reserva.estado in ["PENDING", "RESERVED"]:
                        reserva.estado = "CANCELLED"
            elif status == "RESERVED":
                # Confirmar reservación pendiente o crear una
                space.active = True
                pending = next((r for r in space.reservations if r.estado == "PENDING"), None)
                if pending:
                    pending.estado = "RESERVED"
                else:
                    # Si no hay pendiente, buscar si hay alguna reserva para confirmar
                    existing = next((r for r in space.reservations if r.estado == "RESERVED"), None)
                    if not existing:
                        # Crear una reserva confirmada (admin)
                        new_reserva = Reserva(
                            estado="RESERVED",
                            asignee="Admin",
                            espacio_id=space_id,
                        )
                        db.session.add(new_reserva)
            elif status == "PENDING":
                # Crear reservación pendiente si no existe
                space.active = True
                existing = next((r for r in space.reservations if r.estado in ["PENDING", "RESERVED"]), None)
                if not existing:
                    new_reserva = Reserva(
                        estado="PENDING",
                        asignee="Admin",
                        espacio_id=space_id,
                    )
                    db.session.add(new_reserva)

        db.session.commit()

        # Emitir evento WebSocket para actualizar otros clientes
        space_data = space.to_dict()
        plano_id = str(space.plano_id) if space.plano_id else None
        emit_space_updated(space_data, plano_id)

        return jsonify(space_data), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


@spaces_bp.route("/<string:space_id>/reservar", methods=["POST"])
@require_auth
def reservar_space(space_id):
    """Cliente reserva un stand. Requiere autenticacion. Emite evento WebSocket."""
    space = Space.query.get(space_id)
    if not space:
        return jsonify({"error": "Espacio no encontrado", "status": "error"}), 404

    if not space.active:
        return jsonify({"error": "El stand está bloqueado", "status": "error"}), 400

    data = request.json or {}

    # Obtener datos del usuario autenticado
    current_user = get_current_user()
    user_id = current_user.get("id") if current_user else data.get("user_id")
    asignee = data.get("asignee") or current_user.get("name") if current_user else None

    # Usar el servicio que emite WebSocket
    reserva, error = ReservaService.create_reservation(
        space_id=space_id,
        user_id=user_id,
        asignee=asignee,
    )

    if error:
        return jsonify({"error": error, "status": "error"}), 400

    return jsonify(reserva.to_dict()), 201


@spaces_bp.route("/<string:space_id>/reserva", methods=["DELETE"])
@require_auth
def cancelar_reserva(space_id):
    """Cancelar reserva de un stand. Requiere autenticacion. Emite evento WebSocket."""
    reserva = Reserva.query.filter_by(espacio_id=space_id).first()
    if not reserva:
        return jsonify({"error": "No hay reserva para este stand", "status": "error"}), 404

    try:
        # Guardar datos para el evento antes de eliminar
        reserva_dict = reserva.to_dict()
        space = Space.query.get(space_id)
        plano_id = str(space.plano_id) if space and space.plano_id else None

        db.session.delete(reserva)
        db.session.commit()

        # Emitir evento WebSocket
        emit_reservation_cancelled(reserva_dict, plano_id)

        return jsonify({"message": "Reserva cancelada"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


@spaces_bp.route("/<string:space_id>/bloquear", methods=["PATCH"])
@require_auth
@require_role("Admin")
def bloquear_space(space_id):
    """Admin bloquea un stand. Solo Admin."""
    space = Space.query.get(space_id)
    if not space:
        return jsonify({"error": "Espacio no encontrado", "status": "error"}), 404

    try:
        space.active = False
        db.session.commit()
        return jsonify(space.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


@spaces_bp.route("/<string:space_id>/desbloquear", methods=["PATCH"])
@require_auth
@require_role("Admin")
def desbloquear_space(space_id):
    """Admin desbloquea un stand. Solo Admin."""
    space = Space.query.get(space_id)
    if not space:
        return jsonify({"error": "Espacio no encontrado", "status": "error"}), 404

    try:
        space.active = True
        db.session.commit()
        return jsonify(space.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


@spaces_bp.route("/<string:space_id>/reserva/confirmar", methods=["PATCH"])
@require_auth
@require_role("Admin")
def confirmar_reserva(space_id):
    """Confirmar una reserva pendiente. Solo Admin."""
    reserva = Reserva.query.filter_by(espacio_id=space_id).first()
    if not reserva:
        return jsonify({"error": "No hay reserva para este stand", "status": "error"}), 404

    try:
        reserva.estado = "confirmada"
        db.session.commit()
        return jsonify(reserva.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


# ==================== ENDPOINTS ZONAS ====================

zones_bp = Blueprint("zones", __name__, url_prefix="/zones")


@zones_bp.route("/", methods=["POST"])
@require_auth
@require_role("Admin")
def create_zone():
    """Crear una nueva zona individual. Solo Admin."""
    data = request.json or {}

    # Validar que tenga plano_id
    plano_id = data.get("plano_id")
    if not plano_id:
        return jsonify({"error": "plano_id es requerido", "status": "error"}), 400

    try:
        new_zone = Zone(
            kind=data.get("kind", "rect"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 100),
            height=data.get("height", 100),
            color=data.get("color", "#ffb703"),
            price=data.get("price"),
            name=data.get("name", "Nueva Zona"),
            plano_id=plano_id,
            active=data.get("active", True),
        )
        db.session.add(new_zone)
        db.session.commit()

        return jsonify(new_zone.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


@zones_bp.route("/<string:zone_id>", methods=["GET"])
def get_zone(zone_id):
    """Obtener una zona por ID."""
    zone = Zone.query.get(zone_id)
    if not zone:
        return jsonify({"error": "Zona no encontrada", "status": "error"}), 404
    return jsonify(zone.to_dict()), 200


@zones_bp.route("/<string:zone_id>", methods=["PATCH"])
@require_auth
@require_role("Admin")
def update_zone(zone_id):
    """Actualizar una zona (nombre, precio, color, etc). Solo Admin."""
    zone = Zone.query.get(zone_id)
    if not zone:
        return jsonify({"error": "Zona no encontrada", "status": "error"}), 404

    data = request.json or {}

    try:
        if "name" in data:
            zone.name = data["name"]
        if "description" in data:
            zone.description = data["description"]
        if "price" in data:
            zone.price = data["price"]
        if "color" in data:
            zone.color = data["color"]
        if "active" in data:
            zone.active = data["active"]
        if "x" in data:
            zone.x = data["x"]
        if "y" in data:
            zone.y = data["y"]
        if "width" in data:
            zone.width = data["width"]
        if "height" in data:
            zone.height = data["height"]
        if "rotation" in data:
            zone.rotation = data["rotation"]

        db.session.commit()
        return jsonify(zone.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


@zones_bp.route("/<string:zone_id>", methods=["DELETE"])
@require_auth
@require_role("Admin")
def delete_zone(zone_id):
    """Eliminar una zona por ID. Solo Admin."""
    zone = Zone.query.get(zone_id)
    if not zone:
        return jsonify({"error": "Zona no encontrada", "status": "error"}), 404

    try:
        db.session.delete(zone)
        db.session.commit()
        return jsonify({"message": "Zona eliminada", "id": zone_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


# ==================== DELETE SPACE ====================


@spaces_bp.route("/<string:space_id>", methods=["DELETE"])
@require_auth
@require_role("Admin")
def delete_space(space_id):
    """Eliminar un espacio (stand) por ID. Solo Admin."""
    space = Space.query.get(space_id)
    if not space:
        return jsonify({"error": "Espacio no encontrado", "status": "error"}), 404

    try:
        # Primero eliminar reservas asociadas
        for reserva in space.reservations:
            db.session.delete(reserva)

        plano_id = str(space.plano_id) if space.plano_id else None
        db.session.delete(space)
        db.session.commit()

        # Emitir evento de eliminación
        emit_space_updated({"id": space_id, "deleted": True}, plano_id)

        return jsonify({"message": "Stand eliminado", "id": space_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500
