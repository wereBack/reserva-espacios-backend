"""
Modelo para la entidad Evento.
"""

import uuid
from datetime import datetime, timezone

from database import db

try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    UUID_TYPE = PG_UUID(as_uuid=True)
except ImportError:
    UUID_TYPE = db.String(36)


class Evento(db.Model):
    """
    Representa un evento que agrupa uno o varios planos disponibles para reservas.
    """

    __tablename__ = 'eventos'

    id = db.Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    nombre = db.Column(db.String(150), nullable=False)
    fecha_reserva_desde = db.Column(db.DateTime, nullable=False)
    fecha_reserva_hasta = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relaciones
    planos = db.relationship('Plano', back_populates='evento', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Evento {self.nombre}>'

    def to_dict(self):
        """
        Convierte el modelo a diccionario para serialización JSON.
        """
        return {
            'id': str(self.id),
            'nombre': self.nombre,
            'fecha_reserva_desde': self.fecha_reserva_desde.isoformat() if self.fecha_reserva_desde else None,
            'fecha_reserva_hasta': self.fecha_reserva_hasta.isoformat() if self.fecha_reserva_hasta else None,
            'planos': [plano.to_dict() for plano in self.planos],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia del modelo desde un diccionario.
        """
        return cls(
            nombre=data.get('nombre'),
            fecha_reserva_desde=data.get('fecha_reserva_desde'),
            fecha_reserva_hasta=data.get('fecha_reserva_hasta'),
        )

