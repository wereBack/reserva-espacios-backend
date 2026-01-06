"""
Cliente para validar tokens JWT de Keycloak.
"""

import jwt
import requests
from functools import lru_cache
from typing import Optional, Tuple
from config import settings


class KeycloakTokenValidator:
    """
    Validador de tokens JWT emitidos por Keycloak.
    Obtiene las claves publicas del servidor y valida la firma del token.
    """
    
    def __init__(self):
        # URL interna para conectarse a Keycloak (desde Docker: keycloak:8080)
        self.keycloak_url = settings.KEYCLOAK_URL
        # URL del issuer como aparece en los tokens (desde navegador: localhost:8080)
        self.keycloak_issuer_url = settings.KEYCLOAK_ISSUER_URL
        self.realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_CLIENT_ID
        self._public_key = None
    
    @property
    def issuer_url(self) -> str:
        """URL del issuer de Keycloak (como aparece en los tokens)."""
        return f"{self.keycloak_issuer_url}/realms/{self.realm}"
    
    @property
    def certs_url(self) -> str:
        """URL interna para obtener las claves publicas JWKS."""
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
    
    @lru_cache(maxsize=1)
    def get_public_keys(self) -> dict:
        """
        Obtiene las claves publicas de Keycloak (JWKS).
        Se cachea para evitar llamadas repetidas.
        """
        try:
            response = requests.get(self.certs_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise ValueError(f"Error al obtener claves publicas de Keycloak: {e}")
    
    def _get_signing_key(self, token: str) -> str:
        """
        Obtiene la clave de firma correcta para el token.
        """
        try:
            # Decodificar header sin verificar para obtener kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            jwks = self.get_public_keys()
            
            for key in jwks.get('keys', []):
                if key.get('kid') == kid:
                    # Construir clave publica desde JWK
                    return jwt.algorithms.RSAAlgorithm.from_jwk(key)
            
            raise ValueError(f"No se encontro clave con kid: {kid}")
        except jwt.exceptions.DecodeError as e:
            raise ValueError(f"Token malformado: {e}")
    
    def validate_token(self, token: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Valida un token JWT de Keycloak.
        
        Args:
            token: Token JWT a validar
            
        Returns:
            Tuple[dict, None]: Claims del token si es valido
            Tuple[None, str]: Mensaje de error si es invalido
        """
        try:
            signing_key = self._get_signing_key(token)
            
            # Decodificar y validar el token
            # No verificamos audience porque Keycloak puede usar diferentes valores
            claims = jwt.decode(
                token,
                key=signing_key,
                algorithms=['RS256'],
                issuer=self.issuer_url,
                options={
                    'verify_exp': True,
                    'verify_aud': False,
                    'verify_iss': True,
                }
            )
            
            return claims, None
            
        except jwt.ExpiredSignatureError:
            return None, "Token expirado"
        except jwt.InvalidIssuerError:
            return None, "Issuer del token invalido"
        except jwt.InvalidTokenError as e:
            return None, f"Token invalido: {e}"
        except Exception as e:
            return None, f"Error al validar token: {e}"
    
    def clear_cache(self):
        """Limpia el cache de claves publicas."""
        self.get_public_keys.cache_clear()


# Instancia global del validador
token_validator = KeycloakTokenValidator()

