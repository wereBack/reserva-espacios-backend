"""
Endpoints para gestión de espacios (stands) y reservas.
"""

from flask import Blueprint, request, jsonify
from database import db
from spaces.models.space import Space
from reservas.models.reserva import Reserva

# Blueprint para endpoints de espacios
spaces_bp = Blueprint("spaces", __name__, url_prefix="/spaces")


@spaces_bp.route("/", methods=["GET"])
def get_spaces():
    """Listar todos los espacios."""
    spaces = Space.query.all()
    return jsonify([space.to_dict() for space in spaces]), 200


@spaces_bp.route("/<string:space_id>", methods=["GET"])
def get_space(space_id):
    """Obtener un espacio por ID."""
    space = Space.query.get(space_id)
    if not space:
        return jsonify({"error": "Espacio no encontrado", "status": "error"}), 404
    return jsonify(space.to_dict()), 200


@spaces_bp.route("/<string:space_id>/reservar", methods=["POST"])
def reservar_space(space_id):
    """Cliente reserva un stand."""
    space = Space.query.get(space_id)
    if not space:
        return jsonify({"error": "Espacio no encontrado", "status": "error"}), 404
    
    if not space.active:
        return jsonify({"error": "El stand está bloqueado", "status": "error"}), 400
    
    # Check if already reserved
    existing_reserva = Reserva.query.filter_by(espacio_id=space_id).first()
    if existing_reserva:
        return jsonify({"error": "El stand ya está reservado", "status": "error"}), 400
    
    data = request.json or {}
    
    try:
        reserva = Reserva(
            estado="pendiente",
            asignee=data.get("asignee"),
            user_id=data.get("user_id"),
            espacio_id=space_id,
        )
        db.session.add(reserva)
        db.session.commit()
        return jsonify(reserva.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


@spaces_bp.route("/<string:space_id>/reserva", methods=["DELETE"])
def cancelar_reserva(space_id):
    """Cancelar reserva de un stand."""
    reserva = Reserva.query.filter_by(espacio_id=space_id).first()
    if not reserva:
        return jsonify({"error": "No hay reserva para este stand", "status": "error"}), 404
    
    try:
        db.session.delete(reserva)
        db.session.commit()
        return jsonify({"message": "Reserva cancelada"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "status": "error"}), 500


@spaces_bp.route("/<string:space_id>/bloquear", methods=["PATCH"])
def bloquear_space(space_id):
    """Admin bloquea un stand."""
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
def desbloquear_space(space_id):
    """Admin desbloquea un stand."""
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
def confirmar_reserva(space_id):
    """Confirmar una reserva pendiente."""
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

