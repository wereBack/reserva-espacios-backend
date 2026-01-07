"""
Tests unitarios para modelos SQLAlchemy.
"""

import uuid
from datetime import datetime, timezone
import pytest

from reservas.models.reserva import Reserva
from planos.models.plano import Plano
from spaces.models.space import Space
from spaces.models.polygon import Polygon


class TestReservaModel:
    """Tests para el modelo Reserva."""
    
    def test_to_dict(self, app, db_session, sample_reserva):
        """to_dict() serializa correctamente."""
        with app.app_context():
            data = sample_reserva.to_dict()
            
            assert data['id'] == str(sample_reserva.id)
            assert data['estado'] == 'PENDING'
            assert data['asignee'] == 'Test Asignee'
            assert data['space_id'] == str(sample_reserva.espacio_id)
            assert 'created_at' in data
            assert 'updated_at' in data
    
    def test_to_dict_includes_space_name(self, app, db_session, sample_reserva):
        """to_dict() incluye el nombre del espacio."""
        with app.app_context():
            data = sample_reserva.to_dict()
            
            assert 'space_name' in data
            assert data['space_name'] == 'A1'
    
    def test_to_dict_handles_none_expires_at(self, app, db_session, sample_reserva):
        """to_dict() maneja expires_at None."""
        with app.app_context():
            data = sample_reserva.to_dict()
            
            assert data['expires_at'] is None
    
    def test_from_dict(self, app, db_session, sample_space):
        """from_dict() crea instancia correctamente."""
        with app.app_context():
            data = {
                'estado': 'PENDING',
                'asignee': 'New User',
                'user_id': 'user-123',
                'space_id': str(sample_space.id),
            }
            
            reserva = Reserva.from_dict(data)
            
            assert reserva.estado == 'PENDING'
            assert reserva.asignee == 'New User'
            assert reserva.user_id == 'user-123'
    
    def test_repr(self, app, db_session, sample_reserva):
        """__repr__ devuelve string descriptivo."""
        with app.app_context():
            repr_str = repr(sample_reserva)
            
            assert 'Reserva' in repr_str
            assert 'PENDING' in repr_str


class TestPlanoModel:
    """Tests para el modelo Plano."""
    
    def test_to_dict(self, app, db_session, sample_plano):
        """to_dict() serializa correctamente."""
        with app.app_context():
            data = sample_plano.to_dict()
            
            assert data['id'] == str(sample_plano.id)
            assert data['name'] == 'Plano de Test'
            assert data['url'] == '/test/plano.jpg'
            assert data['width'] == 800
            assert data['height'] == 600
            assert 'created_at' in data
    
    def test_to_dict_without_polygons(self, app, db_session, sample_plano):
        """to_dict() sin include_polygons no incluye polygons."""
        with app.app_context():
            data = sample_plano.to_dict(include_polygons=False)
            
            assert 'polygons' not in data
    
    def test_to_dict_with_polygons(self, app, db_session, sample_plano, sample_space):
        """to_dict() con include_polygons incluye polygons."""
        with app.app_context():
            data = sample_plano.to_dict(include_polygons=True)
            
            assert 'polygons' in data
            assert len(data['polygons']) >= 1
    
    def test_from_dict(self, app, db_session):
        """from_dict() crea instancia correctamente."""
        with app.app_context():
            data = {
                'name': 'Nuevo Plano',
                'url': '/planos/nuevo.jpg',
                'width': 1024,
                'height': 768,
            }
            
            plano = Plano.from_dict(data)
            
            assert plano.name == 'Nuevo Plano'
            assert plano.url == '/planos/nuevo.jpg'
            assert plano.width == 1024
            assert plano.height == 768
    
    def test_repr(self, app, db_session, sample_plano):
        """__repr__ devuelve string descriptivo."""
        with app.app_context():
            repr_str = repr(sample_plano)
            
            assert 'Plano' in repr_str


class TestSpaceModel:
    """Tests para el modelo Space."""
    
    def test_to_dict(self, app, db_session, sample_space):
        """to_dict() serializa correctamente."""
        with app.app_context():
            data = sample_space.to_dict()
            
            assert data['name'] == 'A1'
            assert data['kind'] == 'rect'
            assert data['active'] is True
            assert data['x'] == 100.0
            assert data['y'] == 100.0
            assert data['width'] == 50.0
            assert data['height'] == 50.0
            assert data['color'] == '#ffb703'
    
    def test_to_dict_includes_reservations(self, app, db_session, sample_reserva):
        """to_dict() incluye reservaciones."""
        with app.app_context():
            # sample_reserva esta asociada al espacio
            space = sample_reserva.space
            data = space.to_dict()
            
            assert 'reservations' in data
            assert len(data['reservations']) == 1
    
    def test_from_dict(self, app, db_session, sample_plano):
        """from_dict() crea instancia correctamente."""
        with app.app_context():
            data = {
                'name': 'B2',
                'kind': 'rect',
                'x': 200,
                'y': 200,
                'width': 60,
                'height': 60,
                'color': '#00ff00',
                'plano_id': str(sample_plano.id),
                'active': True,
            }
            
            space = Space.from_dict(data)
            
            assert space.name == 'B2'
            assert space.kind == 'rect'
            assert space.active is True
    
    def test_inactive_space(self, app, db_session, inactive_space):
        """Espacio inactivo tiene active=False."""
        with app.app_context():
            data = inactive_space.to_dict()
            
            assert data['active'] is False
    
    def test_repr(self, app, db_session, sample_space):
        """__repr__ devuelve string descriptivo."""
        with app.app_context():
            repr_str = repr(sample_space)
            
            assert 'Space' in repr_str
            assert 'A1' in repr_str


class TestPolygonModel:
    """Tests para el modelo Polygon (clase base)."""
    
    def test_to_dict(self, app, db_session, sample_plano):
        """to_dict() serializa correctamente."""
        with app.app_context():
            polygon = Polygon(
                kind='rect',
                x=50,
                y=50,
                width=100,
                height=100,
                color='#aabbcc',
                plano_id=sample_plano.id,
            )
            db_session.add(polygon)
            db_session.commit()
            
            data = polygon.to_dict()
            
            assert data['kind'] == 'rect'
            assert data['x'] == 50.0
            assert data['y'] == 50.0
            assert data['width'] == 100.0
            assert data['height'] == 100.0
            assert data['color'] == '#aabbcc'
    
    def test_to_dict_handles_none_price(self, app, db_session, sample_plano):
        """to_dict() maneja price None."""
        with app.app_context():
            polygon = Polygon(
                kind='rect',
                x=0,
                y=0,
                width=50,
                height=50,
                color='#ffffff',
                plano_id=sample_plano.id,
                price=None,
            )
            db_session.add(polygon)
            db_session.commit()
            
            data = polygon.to_dict()
            
            assert data['price'] is None
    
    def test_to_dict_with_price(self, app, db_session, sample_plano):
        """to_dict() serializa precio correctamente."""
        with app.app_context():
            polygon = Polygon(
                kind='rect',
                x=0,
                y=0,
                width=50,
                height=50,
                color='#ffffff',
                plano_id=sample_plano.id,
                price=1500.50,
            )
            db_session.add(polygon)
            db_session.commit()
            
            data = polygon.to_dict()
            
            assert data['price'] == 1500.50
    
    def test_from_dict_generates_uuid_if_missing(self, app, db_session, sample_plano):
        """from_dict() genera UUID si no se proporciona."""
        with app.app_context():
            data = {
                'kind': 'rect',
                'x': 0,
                'y': 0,
                'width': 50,
                'height': 50,
                'color': '#ffffff',
                'plano_id': str(sample_plano.id),
            }
            
            polygon = Polygon.from_dict(data)
            
            assert polygon.id is not None
    
    def test_from_dict_uses_provided_uuid(self, app, db_session, sample_plano):
        """from_dict() usa UUID proporcionado."""
        with app.app_context():
            provided_id = uuid.uuid4()
            data = {
                'id': str(provided_id),
                'kind': 'rect',
                'x': 0,
                'y': 0,
                'width': 50,
                'height': 50,
                'color': '#ffffff',
                'plano_id': str(sample_plano.id),
            }
            
            polygon = Polygon.from_dict(data)
            
            assert polygon.id == provided_id

