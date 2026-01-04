from flask import Blueprint, request, jsonify
from database import db
from planos.models.plano import Plano
from spaces.models.space import Space
from spaces.models.zone import Zone
from spaces.models.polygon import Polygon
from services.s3_service import upload_file

planos_bp = Blueprint('planos_bp', __name__, url_prefix='/planos')


@planos_bp.route('/upload-image', methods=['POST'])
def upload_plano_image():
    """Sube una imagen de plano a S3 y retorna la URL pública."""
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo', 'status': 'error', 'code': 400}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío', 'status': 'error', 'code': 400}), 400
    
    try:
        url = upload_file(file, file.filename, file.content_type)
        return jsonify({'url': url}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error', 'code': 500}), 500


def plano_to_full_dict(plano):
    """Convert plano to dict including spaces and zones."""
    data = plano.to_dict()
    # Query spaces and zones for this plano
    spaces = Space.query.filter_by(plano_id=plano.id).all()
    zones = Zone.query.filter_by(plano_id=plano.id).all()
    data['spaces'] = [space.to_dict() for space in spaces]
    data['zones'] = [zone.to_dict() for zone in zones]
    return data


@planos_bp.route('/', methods=['GET'])
def list_planos():
    planos = Plano.query.all()
    return jsonify([plano_to_full_dict(plano) for plano in planos]), 200


@planos_bp.route('/por-evento/<string:evento_id>', methods=['GET'])
def list_planos_by_evento(evento_id):
    """Lista planos filtrados por evento."""
    planos = Plano.query.filter_by(evento_id=evento_id).all()
    return jsonify([plano_to_full_dict(plano) for plano in planos]), 200

@planos_bp.route('/<string:plano_id>', methods=['GET'])
def get_plano(plano_id):
    plano = Plano.query.get(plano_id)
    if not plano:
        return jsonify({'error': 'Plano no encontrado', 'status': 'error', 'code': 404}), 404
    return jsonify(plano_to_full_dict(plano)), 200

@planos_bp.route('/', methods=['POST'])
def create_plano():
    data = request.json
    if not data:
        return jsonify({'error': 'Datos inválidos', 'status': 'error', 'code': 400}), 400

    try:
        new_plano = Plano(
            name=data.get('name'),
            width=data.get('width'),
            height=data.get('height'),
            url=data.get('url'),
            evento_id=data.get('evento_id')
        )
        db.session.add(new_plano)
        db.session.flush()

        # Crear Zonas PRIMERO (para tener los IDs disponibles)
        zones_data = data.get('zones', [])
        zone_id_map = {}  # Mapea frontend ID -> backend ID
        for zone_data in zones_data:
            new_zone = Zone(
                kind=zone_data.get('kind', 'rect'),
                x=zone_data.get('x'),
                y=zone_data.get('y'),
                width=zone_data.get('width'),
                height=zone_data.get('height'),
                color=zone_data.get('color'),
                price=zone_data.get('price'),
                name=zone_data.get('name'),
                plano_id=new_plano.id,
                active=True
            )
            db.session.add(new_zone)
            db.session.flush()  # Obtener ID generado
            frontend_id = zone_data.get('id')
            if frontend_id:
                zone_id_map[frontend_id] = str(new_zone.id)

        # Crear Espacios CON zone_id
        spaces_data = data.get('spaces', [])
        for space_data in spaces_data:
            # Traducir zone_id del frontend al backend
            frontend_zone_id = space_data.get('zone_id')
            backend_zone_id = zone_id_map.get(frontend_zone_id) if frontend_zone_id else None
            
            new_space = Space(
                kind=space_data.get('kind', 'rect'),
                x=space_data.get('x'),
                y=space_data.get('y'),
                width=space_data.get('width'),
                height=space_data.get('height'),
                color=space_data.get('color'),
                price=space_data.get('price'),
                name=space_data.get('name'),
                plano_id=new_plano.id,
                zone_id=backend_zone_id,
                active=True
            )
            db.session.add(new_space)

        db.session.commit()
        return jsonify(plano_to_full_dict(new_plano)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'status': 'error', 'code': 500}), 500

@planos_bp.route('/<string:plano_id>', methods=['PUT'])
def update_plano(plano_id):
    plano = Plano.query.get(plano_id)
    if not plano:
        return jsonify({'error': 'Plano no encontrado', 'status': 'error', 'code': 404}), 404

    data = request.json
    try:
        plano.name = data.get('name', plano.name)
        plano.width = data.get('width', plano.width)
        plano.height = data.get('height', plano.height)
        plano.url = data.get('url', plano.url)
        plano.evento_id = data.get('evento_id', plano.evento_id)

        # Limpiar espacios y zonas existentes (simple replacement strategy)
        # Ojo: esto borra todo y recrea. Idealmente sería update inteligente pero esto basta por ahora.
        # Primero borrar hijos para evitar orphans
        existing_spaces = Space.query.filter_by(plano_id=plano.id).all()
        for space in existing_spaces:
            db.session.delete(space)
        existing_zones = Zone.query.filter_by(plano_id=plano.id).all()
        for zone in existing_zones:
            db.session.delete(zone)
        
        db.session.flush()

        # Recrear Zonas PRIMERO (para tener los IDs disponibles)
        zones_data = data.get('zones', [])
        zone_id_map = {}  # Mapea frontend ID -> backend ID
        for zone_data in zones_data:
            new_zone = Zone(
                kind=zone_data.get('kind', 'rect'),
                x=zone_data.get('x'),
                y=zone_data.get('y'),
                width=zone_data.get('width'),
                height=zone_data.get('height'),
                color=zone_data.get('color'),
                price=zone_data.get('price'),
                name=zone_data.get('name'),
                plano_id=plano.id,
                active=True
            )
            db.session.add(new_zone)
            db.session.flush()  # Obtener ID generado
            frontend_id = zone_data.get('id')
            if frontend_id:
                zone_id_map[frontend_id] = str(new_zone.id)

        # Recrear Espacios CON zone_id
        spaces_data = data.get('spaces', [])
        for space_data in spaces_data:
            # Traducir zone_id del frontend al backend
            frontend_zone_id = space_data.get('zone_id')
            backend_zone_id = zone_id_map.get(frontend_zone_id) if frontend_zone_id else None
            
            new_space = Space(
                kind=space_data.get('kind', 'rect'),
                x=space_data.get('x'),
                y=space_data.get('y'),
                width=space_data.get('width'),
                height=space_data.get('height'),
                color=space_data.get('color'),
                price=space_data.get('price'),
                name=space_data.get('name'),
                plano_id=plano.id,
                zone_id=backend_zone_id,
                active=True
            )
            db.session.add(new_space)

        db.session.commit()
        return jsonify(plano_to_full_dict(plano)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'status': 'error', 'code': 500}), 500

@planos_bp.route('/<string:plano_id>', methods=['DELETE'])
def delete_plano(plano_id):
    plano = Plano.query.get(plano_id)
    if not plano:
        return jsonify({'error': 'Plano no encontrado', 'status': 'error', 'code': 404}), 404

    try:
        db.session.delete(plano)
        db.session.commit()
        return jsonify({'message': 'Plano eliminado'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'status': 'error', 'code': 500}), 500
