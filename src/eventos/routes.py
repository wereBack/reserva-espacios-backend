from flask import Blueprint, request, jsonify
from database import db
from eventos.models.evento import Evento
from datetime import datetime

eventos_bp = Blueprint('eventos_bp', __name__, url_prefix='/eventos')

@eventos_bp.route('/', methods=['GET'])
def list_eventos():
    eventos = Evento.query.all()
    return jsonify([evento.to_dict() for evento in eventos]), 200

@eventos_bp.route('/', methods=['POST'])
def create_evento():
    data = request.json
    if not data:
        return jsonify({'error': 'Datos inválidos', 'status': 'error', 'code': 400}), 400
    
    try:
        # Parse dates
        fecha_desde = datetime.fromisoformat(data.get('fecha_reserva_desde').replace('Z', '+00:00')) if data.get('fecha_reserva_desde') else None
        fecha_hasta = datetime.fromisoformat(data.get('fecha_reserva_hasta').replace('Z', '+00:00')) if data.get('fecha_reserva_hasta') else None

        new_evento = Evento(
            nombre=data.get('nombre'),
            fecha_reserva_desde=fecha_desde,
            fecha_reserva_hasta=fecha_hasta
        )
        db.session.add(new_evento)
        db.session.commit()
        return jsonify(new_evento.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'status': 'error', 'code': 500}), 500
