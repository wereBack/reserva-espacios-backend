"""
Modulo de autenticacion con Keycloak.
Proporciona decoradores para proteger rutas y validar tokens JWT.
"""

from auth.decorators import get_current_user, require_auth, require_role
from auth.keycloak import KeycloakTokenValidator

__all__ = ["require_auth", "require_role", "get_current_user", "KeycloakTokenValidator"]
