"""
Decoradores para proteger rutas con autenticacion JWT.
"""

import logging
from functools import wraps
from typing import List, Optional
from flask import request, jsonify, g
from auth.keycloak import token_validator

logger = logging.getLogger(__name__)


def get_token_from_request() -> Optional[str]:
    """
    Extrae el token JWT del header Authorization.
    Formato esperado: "Bearer <token>"
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return None
    
    parts = auth_header.split()
    
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]


def get_current_user() -> Optional[dict]:
    """
    Obtiene el usuario actual del contexto de la request.
    Debe usarse dentro de una ruta protegida con @require_auth.
    
    Returns:
        dict con la informacion del usuario o None
    """
    return getattr(g, 'current_user', None)


def require_auth(f):
    """
    Decorador que requiere autenticacion valida.
    El token debe estar en el header Authorization como "Bearer <token>".
    
    Si el token es valido, guarda los claims en g.current_user.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            logger.warning("Peticion sin token de autenticacion")
            return jsonify({
                'error': 'Token de autenticacion requerido',
                'status': 'error',
                'code': 401
            }), 401
        
        claims, error = token_validator.validate_token(token)
        
        if error:
            logger.warning(f"Error validando token: {error}")
            return jsonify({
                'error': error,
                'status': 'error',
                'code': 401
            }), 401
        
        # Guardar claims del usuario en el contexto
        g.current_user = {
            'id': claims.get('sub'),
            'username': claims.get('preferred_username'),
            'email': claims.get('email'),
            'name': claims.get('name'),
            'roles': _extract_roles(claims),
            'claims': claims
        }
        
        return f(*args, **kwargs)
    
    return decorated


def require_role(*required_roles: str):
    """
    Decorador que requiere uno o mas roles especificos.
    Debe usarse DESPUES de @require_auth.
    
    Args:
        *required_roles: Roles requeridos (el usuario debe tener AL MENOS uno)
        
    Ejemplo:
        @app.route('/admin')
        @require_auth
        @require_role('Admin')
        def admin_only():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Verificar que el usuario esta autenticado
            current_user = get_current_user()
            
            if not current_user:
                return jsonify({
                    'error': 'Autenticacion requerida',
                    'status': 'error',
                    'code': 401
                }), 401
            
            user_roles = current_user.get('roles', [])
            
            # Verificar si el usuario tiene alguno de los roles requeridos
            has_required_role = any(role in user_roles for role in required_roles)
            
            if not has_required_role:
                return jsonify({
                    'error': f'Acceso denegado. Se requiere uno de los roles: {", ".join(required_roles)}',
                    'status': 'error',
                    'code': 403
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated
    
    return decorator


def _extract_roles(claims: dict) -> List[str]:
    """
    Extrae los roles del token JWT de Keycloak.
    Los roles pueden estar en realm_access y/o resource_access.
    """
    roles = []
    
    # Roles del realm
    realm_access = claims.get('realm_access', {})
    roles.extend(realm_access.get('roles', []))
    
    # Roles del cliente (resource_access)
    resource_access = claims.get('resource_access', {})
    for client, access in resource_access.items():
        roles.extend(access.get('roles', []))
    
    return list(set(roles))  # Eliminar duplicados

