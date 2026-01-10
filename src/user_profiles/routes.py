"""
Rutas REST para gestión de perfiles de usuario.
"""

from flask import Blueprint, jsonify, request
from database import db
from auth import require_auth, require_role, get_current_user
from user_profiles.models.user_profile import UserProfile

user_profiles_bp = Blueprint('user_profiles', __name__, url_prefix='/api/user-profiles')


@user_profiles_bp.route('/me', methods=['GET'])
@require_auth
def get_my_profile():
    """
    Obtener el perfil del usuario autenticado.
    Si no existe, retorna un perfil vacío.
    
    Returns:
        200: Perfil del usuario
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') if current_user else None
        
        if not user_id:
            return jsonify({
                'error': 'Usuario no identificado',
                'status': 'error'
            }), 401
        
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        if profile:
            return jsonify({
                'status': 'success',
                'profile': profile.to_dict(),
                'is_complete': profile.is_complete()
            }), 200
        else:
            # Retornar perfil vacío si no existe
            return jsonify({
                'status': 'success',
                'profile': {
                    'user_id': user_id,
                    'email': None,
                    'phone': None,
                    'linkedin': None,
                    'company': None,
                    'position': None,
                    'notes': None,
                },
                'is_complete': False
            }), 200
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@user_profiles_bp.route('/me', methods=['PUT'])
@require_auth
def update_my_profile():
    """
    Actualizar el perfil del usuario autenticado.
    Crea el perfil si no existe.
    
    Request Body:
        {
            "email": "email@example.com",
            "phone": "+598...",
            "linkedin": "https://linkedin.com/in/...",
            "company": "Empresa",
            "position": "Cargo",
            "notes": "Notas adicionales"
        }
        
    Returns:
        200: Perfil actualizado
        400: Datos inválidos
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') if current_user else None
        
        if not user_id:
            return jsonify({
                'error': 'Usuario no identificado',
                'status': 'error'
            }), 401
        
        data = request.get_json() or {}
        
        # Buscar perfil existente o crear uno nuevo
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        if profile:
            # Actualizar campos existentes
            profile.email = data.get('email', profile.email)
            profile.phone = data.get('phone', profile.phone)
            profile.linkedin = data.get('linkedin', profile.linkedin)
            profile.company = data.get('company', profile.company)
            profile.position = data.get('position', profile.position)
            profile.notes = data.get('notes', profile.notes)
        else:
            # Crear nuevo perfil
            profile = UserProfile.from_dict(data, user_id)
            db.session.add(profile)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Perfil actualizado exitosamente',
            'profile': profile.to_dict(),
            'is_complete': profile.is_complete()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@user_profiles_bp.route('/me/complete', methods=['GET'])
@require_auth
def check_profile_complete():
    """
    Verificar si el perfil del usuario está completo.
    
    Returns:
        200: { is_complete: bool, missing_fields: [...] }
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') if current_user else None
        
        if not user_id:
            return jsonify({
                'error': 'Usuario no identificado',
                'status': 'error'
            }), 401
        
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        missing_fields = []
        is_complete = False
        
        if profile:
            is_complete = profile.is_complete()
            if not profile.email or not profile.email.strip():
                missing_fields.append('email')
        else:
            missing_fields.append('email')
        
        return jsonify({
            'status': 'success',
            'is_complete': is_complete,
            'missing_fields': missing_fields
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@user_profiles_bp.route('/by-id/<path:user_id>', methods=['GET'])
@require_auth
@require_role('Admin')
def get_user_profile_by_id(user_id):
    """
    Obtener el perfil de cualquier usuario por su ID. Solo Admin.
    
    Args:
        user_id: ID del usuario
        
    Returns:
        200: Perfil del usuario
        404: Perfil no encontrado
    """
    try:
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        if profile:
            return jsonify({
                'status': 'success',
                'profile': profile.to_dict()
            }), 200
        else:
            # Perfil no existe aún
            return jsonify({
                'status': 'success',
                'profile': {
                    'user_id': user_id,
                    'email': None,
                    'phone': None,
                    'linkedin': None,
                    'company': None,
                    'position': None,
                    'notes': None,
                }
            }), 200
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500
