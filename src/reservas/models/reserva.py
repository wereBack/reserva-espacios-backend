"""
Modelo para la entidad Reserva.
"""

import uuid
from datetime import datetime, timezone

from database import db

try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    UUID_TYPE = PG_UUID(as_uuid=True)
except ImportError:
    UUID_TYPE = db.String(36)


class Reserva(db.Model):
    """
    Reserva asociada a un espacio y realizada por un usuario externo (Keycloak).
    """

    __tablename__ = 'reservas'

    id = db.Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    estado = db.Column(db.String(30), nullable=False)
    asignee = db.Column(db.String(120), nullable=True)
    user_id = db.Column(db.String(120), nullable=True)
    espacio_id = db.Column(UUID_TYPE, db.ForeignKey('spaces.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relaciones
    space = db.relationship('Space', back_populates='reservations', lazy=True)

    def __repr__(self):
        return f'<Reserva {self.id} estado={self.estado}>'

    def to_dict(self):
        """
        Convierte el modelo a diccionario para serialización JSON.
        """
        return {
            'id': str(self.id),
            'estado': self.estado,
            'asignee': self.asignee,
            'user_id': self.user_id,
            'space_id': str(self.espacio_id),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia de Reserva desde un diccionario.
        """
        return cls(
            estado=data.get('estado'),
            asignee=data.get('asignee'),
            user_id=data.get('user_id'),
            espacio_id=data.get('space_id'),
        )

