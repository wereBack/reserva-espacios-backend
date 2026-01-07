"""
Fixtures globales para tests del backend.
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock

# Importar antes de crear la app para evitar problemas con gevent
import sys
sys.modules['gevent'] = MagicMock()
sys.modules['gevent.monkey'] = MagicMock()

from flask import Flask
from database import db


# ==================== FIXTURES DE APLICACION ====================

@pytest.fixture(scope='function')
def app():
    """
    Crea una instancia de la aplicacion Flask para testing.
    Usa SQLite en memoria para tests rapidos.
    """
    # Mock de WebSocket para evitar inicializacion
    with patch('websocket.init_socketio'), \
         patch('websocket.socketio'):
        
        # Crear app Flask directamente para tests
        flask_app = Flask(__name__)
        flask_app.config['TESTING'] = True
        flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        flask_app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Inicializar extensiones
        db.init_app(flask_app)
        
        # Registrar blueprints
        from health.routes import health_bp
        from spaces.routes import spaces_bp, zones_bp
        from eventos.routes import eventos_bp
        from planos.routes import planos_bp
        from reservas.routes import reservas_bp
        
        flask_app.register_blueprint(health_bp)
        flask_app.register_blueprint(spaces_bp)
        flask_app.register_blueprint(zones_bp)
        flask_app.register_blueprint(eventos_bp)
        flask_app.register_blueprint(planos_bp)
        flask_app.register_blueprint(reservas_bp)
        
        with flask_app.app_context():
            # Crear todas las tablas
            db.create_all()
            yield flask_app
            # Limpiar despues de cada test
            db.session.remove()
            db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Cliente de pruebas HTTP."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Sesion de base de datos limpia por test."""
    with app.app_context():
        yield db.session
        db.session.rollback()


# ==================== FIXTURES DE AUTENTICACION ====================

@pytest.fixture
def mock_token_validator():
    """
    Mock del validador de tokens de Keycloak.
    Permite simular autenticacion sin Keycloak real.
    Patchea donde se usa (en decorators), no donde se define.
    """
    with patch('auth.decorators.token_validator') as mock_validator:
        yield mock_validator


@pytest.fixture
def valid_user_claims():
    """Claims de un usuario normal autenticado."""
    return {
        'sub': str(uuid.uuid4()),
        'preferred_username': 'testuser',
        'email': 'test@example.com',
        'name': 'Test User',
        'realm_access': {'roles': ['user']},
        'resource_access': {},
    }


@pytest.fixture
def admin_user_claims():
    """Claims de un usuario administrador."""
    return {
        'sub': str(uuid.uuid4()),
        'preferred_username': 'adminuser',
        'email': 'admin@example.com',
        'name': 'Admin User',
        'realm_access': {'roles': ['Admin', 'user']},
        'resource_access': {'front-admin': {'roles': ['Admin']}},
    }


@pytest.fixture
def auth_headers(valid_user_claims, mock_token_validator):
    """
    Headers con token JWT mockeado para usuario normal.
    Configura el mock para aceptar el token.
    """
    mock_token_validator.validate_token.return_value = (valid_user_claims, None)
    return {'Authorization': 'Bearer valid-test-token'}


@pytest.fixture
def admin_auth_headers(admin_user_claims, mock_token_validator):
    """
    Headers con token JWT mockeado para usuario admin.
    """
    mock_token_validator.validate_token.return_value = (admin_user_claims, None)
    return {'Authorization': 'Bearer admin-test-token'}


@pytest.fixture
def invalid_auth_headers(mock_token_validator):
    """
    Headers con token invalido.
    """
    mock_token_validator.validate_token.return_value = (None, 'Token invalido')
    return {'Authorization': 'Bearer invalid-token'}


# ==================== FIXTURES DE DATOS ====================

@pytest.fixture
def sample_plano(app, db_session):
    """Crea un plano de ejemplo en la BD."""
    from planos.models.plano import Plano
    
    plano = Plano(
        id=uuid.uuid4(),
        name='Plano de Test',
        url='/test/plano.jpg',
        width=800,
        height=600,
    )
    db_session.add(plano)
    db_session.commit()
    return plano


@pytest.fixture
def sample_space(app, db_session, sample_plano):
    """Crea un espacio de ejemplo en la BD."""
    from spaces.models.space import Space
    
    space = Space(
        id=uuid.uuid4(),
        name='A1',
        kind='rect',
        x=100,
        y=100,
        width=50,
        height=50,
        color='#ffb703',
        plano_id=sample_plano.id,
        active=True,
    )
    db_session.add(space)
    db_session.commit()
    return space


@pytest.fixture
def inactive_space(app, db_session, sample_plano):
    """Crea un espacio inactivo (bloqueado)."""
    from spaces.models.space import Space
    
    space = Space(
        id=uuid.uuid4(),
        name='B1',
        kind='rect',
        x=200,
        y=100,
        width=50,
        height=50,
        color='#cccccc',
        plano_id=sample_plano.id,
        active=False,
    )
    db_session.add(space)
    db_session.commit()
    return space


@pytest.fixture
def sample_reserva(app, db_session, sample_space):
    """Crea una reserva de ejemplo en estado PENDING."""
    from reservas.models.reserva import Reserva
    
    reserva = Reserva(
        id=uuid.uuid4(),
        espacio_id=sample_space.id,
        user_id=str(uuid.uuid4()),
        asignee='Test Asignee',
        estado='PENDING',
    )
    db_session.add(reserva)
    db_session.commit()
    return reserva


@pytest.fixture
def confirmed_reserva(app, db_session, sample_space):
    """Crea una reserva confirmada (RESERVED)."""
    from reservas.models.reserva import Reserva
    
    reserva = Reserva(
        id=uuid.uuid4(),
        espacio_id=sample_space.id,
        user_id=str(uuid.uuid4()),
        asignee='Confirmed User',
        estado='RESERVED',
    )
    db_session.add(reserva)
    db_session.commit()
    return reserva

