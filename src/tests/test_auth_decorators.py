"""
Tests unitarios para decoradores de autenticacion.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask, jsonify, g

from auth.decorators import (
    get_token_from_request,
    get_current_user,
    require_auth,
    require_role,
    _extract_roles,
)


class TestGetTokenFromRequest:
    """Tests para get_token_from_request()"""
    
    def test_extract_valid_bearer_token(self, app):
        """Extrae token de header Authorization valido."""
        with app.test_request_context(
            headers={'Authorization': 'Bearer my-jwt-token'}
        ):
            token = get_token_from_request()
            assert token == 'my-jwt-token'
    
    def test_extract_token_case_insensitive(self, app):
        """Bearer es case-insensitive."""
        with app.test_request_context(
            headers={'Authorization': 'bearer my-jwt-token'}
        ):
            token = get_token_from_request()
            assert token == 'my-jwt-token'
    
    def test_no_authorization_header(self, app):
        """Retorna None si no hay header Authorization."""
        with app.test_request_context():
            token = get_token_from_request()
            assert token is None
    
    def test_empty_authorization_header(self, app):
        """Retorna None si header esta vacio."""
        with app.test_request_context(headers={'Authorization': ''}):
            token = get_token_from_request()
            assert token is None
    
    def test_invalid_format_no_bearer(self, app):
        """Retorna None si falta 'Bearer'."""
        with app.test_request_context(headers={'Authorization': 'my-jwt-token'}):
            token = get_token_from_request()
            assert token is None
    
    def test_invalid_format_basic_auth(self, app):
        """Retorna None para Basic auth."""
        with app.test_request_context(
            headers={'Authorization': 'Basic dXNlcjpwYXNz'}
        ):
            token = get_token_from_request()
            assert token is None
    
    def test_invalid_format_extra_parts(self, app):
        """Retorna None si hay partes extra."""
        with app.test_request_context(
            headers={'Authorization': 'Bearer token extra-part'}
        ):
            token = get_token_from_request()
            assert token is None


class TestExtractRoles:
    """Tests para _extract_roles()"""
    
    def test_extract_realm_roles(self):
        """Extrae roles del realm."""
        claims = {
            'realm_access': {'roles': ['user', 'viewer']},
        }
        roles = _extract_roles(claims)
        assert 'user' in roles
        assert 'viewer' in roles
    
    def test_extract_resource_roles(self):
        """Extrae roles de resource_access."""
        claims = {
            'resource_access': {
                'front-admin': {'roles': ['Admin', 'editor']},
                'api-client': {'roles': ['api-user']},
            },
        }
        roles = _extract_roles(claims)
        assert 'Admin' in roles
        assert 'editor' in roles
        assert 'api-user' in roles
    
    def test_extract_combined_roles(self):
        """Combina roles de realm y resources."""
        claims = {
            'realm_access': {'roles': ['user']},
            'resource_access': {
                'front-admin': {'roles': ['Admin']},
            },
        }
        roles = _extract_roles(claims)
        assert 'user' in roles
        assert 'Admin' in roles
    
    def test_deduplicate_roles(self):
        """Elimina roles duplicados."""
        claims = {
            'realm_access': {'roles': ['Admin', 'user']},
            'resource_access': {
                'client': {'roles': ['Admin']},
            },
        }
        roles = _extract_roles(claims)
        assert roles.count('Admin') == 1
    
    def test_empty_claims(self):
        """Retorna lista vacia si no hay claims de roles."""
        roles = _extract_roles({})
        assert roles == []
    
    def test_missing_roles_key(self):
        """Maneja falta de key 'roles'."""
        claims = {
            'realm_access': {},
            'resource_access': {'client': {}},
        }
        roles = _extract_roles(claims)
        assert roles == []


class TestRequireAuthDecorator:
    """Tests para @require_auth"""
    
    def test_allows_valid_token(self, app, mock_token_validator, valid_user_claims):
        """Permite acceso con token valido."""
        mock_token_validator.validate_token.return_value = (valid_user_claims, None)
        
        @app.route('/test-auth')
        @require_auth
        def protected_route():
            return jsonify({'status': 'ok'})
        
        with app.test_client() as client:
            response = client.get(
                '/test-auth',
                headers={'Authorization': 'Bearer valid-token'}
            )
            assert response.status_code == 200
    
    def test_rejects_missing_token(self, app):
        """Rechaza request sin token."""
        @app.route('/test-no-token')
        @require_auth
        def protected_route():
            return jsonify({'status': 'ok'})
        
        with app.test_client() as client:
            response = client.get('/test-no-token')
            assert response.status_code == 401
            data = response.get_json()
            assert 'requerido' in data['error'].lower()
    
    def test_rejects_invalid_token(self, app, mock_token_validator):
        """Rechaza token invalido."""
        mock_token_validator.validate_token.return_value = (None, 'Token invalido')
        
        @app.route('/test-invalid')
        @require_auth
        def protected_route():
            return jsonify({'status': 'ok'})
        
        with app.test_client() as client:
            response = client.get(
                '/test-invalid',
                headers={'Authorization': 'Bearer invalid-token'}
            )
            assert response.status_code == 401
    
    def test_sets_current_user_in_context(
        self, app, mock_token_validator, valid_user_claims
    ):
        """Guarda usuario en g.current_user."""
        mock_token_validator.validate_token.return_value = (valid_user_claims, None)
        
        captured_user = {}
        
        @app.route('/test-context')
        @require_auth
        def protected_route():
            captured_user['user'] = get_current_user()
            return jsonify({'status': 'ok'})
        
        with app.test_client() as client:
            client.get(
                '/test-context',
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert captured_user['user'] is not None
        assert captured_user['user']['username'] == 'testuser'


class TestRequireRoleDecorator:
    """Tests para @require_role"""
    
    def test_allows_user_with_required_role(
        self, app, mock_token_validator, admin_user_claims
    ):
        """Permite acceso si usuario tiene el rol requerido."""
        mock_token_validator.validate_token.return_value = (admin_user_claims, None)
        
        @app.route('/test-admin')
        @require_auth
        @require_role('Admin')
        def admin_route():
            return jsonify({'status': 'ok'})
        
        with app.test_client() as client:
            response = client.get(
                '/test-admin',
                headers={'Authorization': 'Bearer admin-token'}
            )
            assert response.status_code == 200
    
    def test_rejects_user_without_required_role(
        self, app, mock_token_validator, valid_user_claims
    ):
        """Rechaza si usuario no tiene el rol requerido."""
        mock_token_validator.validate_token.return_value = (valid_user_claims, None)
        
        @app.route('/test-admin-only')
        @require_auth
        @require_role('Admin')
        def admin_route():
            return jsonify({'status': 'ok'})
        
        with app.test_client() as client:
            response = client.get(
                '/test-admin-only',
                headers={'Authorization': 'Bearer user-token'}
            )
            assert response.status_code == 403
            data = response.get_json()
            assert 'denegado' in data['error'].lower()
    
    def test_allows_any_of_multiple_roles(
        self, app, mock_token_validator, admin_user_claims
    ):
        """Permite si usuario tiene alguno de los roles requeridos."""
        mock_token_validator.validate_token.return_value = (admin_user_claims, None)
        
        @app.route('/test-multi-role')
        @require_auth
        @require_role('SuperAdmin', 'Admin')
        def multi_role_route():
            return jsonify({'status': 'ok'})
        
        with app.test_client() as client:
            response = client.get(
                '/test-multi-role',
                headers={'Authorization': 'Bearer admin-token'}
            )
            assert response.status_code == 200
    
    def test_requires_auth_before_role_check(self, app):
        """require_role sin autenticacion retorna 401."""
        @app.route('/test-role-no-auth')
        @require_role('Admin')
        def unprotected_role_route():
            return jsonify({'status': 'ok'})
        
        with app.test_client() as client:
            response = client.get('/test-role-no-auth')
            # Sin @require_auth, g.current_user no existe
            assert response.status_code == 401


class TestGetCurrentUser:
    """Tests para get_current_user()"""
    
    def test_returns_user_when_set(self, app):
        """Retorna usuario del contexto."""
        with app.test_request_context():
            g.current_user = {'id': '123', 'username': 'test'}
            user = get_current_user()
            assert user['id'] == '123'
    
    def test_returns_none_when_not_set(self, app):
        """Retorna None si no hay usuario en contexto."""
        with app.test_request_context():
            user = get_current_user()
            assert user is None

