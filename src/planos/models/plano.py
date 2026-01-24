"""
Modelo para la entidad Plano.
"""

import uuid
from datetime import UTC, datetime

from database import db

try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    UUID_TYPE = PG_UUID(as_uuid=True)
except ImportError:
    UUID_TYPE = db.String(36)


class Plano(db.Model):
    """
    Plano sobre el cual se pintan zonas y espacios.
    """

    __tablename__ = "planos"

    id = db.Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(150), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    pixels_per_meter = db.Column(db.Float, nullable=True)  # Scale calibration
    evento_id = db.Column(UUID_TYPE, db.ForeignKey("eventos.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relaciones
    evento = db.relationship("Evento", back_populates="planos", lazy=True)
    polygons = db.relationship("Polygon", back_populates="plano", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plano {self.name}>"

    def to_dict(self, include_polygons=False):
        """
        Convierte el modelo a diccionario para serialización JSON.
        """
        data = {
            "id": str(self.id),
            "name": self.name,
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "pixels_per_meter": self.pixels_per_meter,
            "evento_id": str(self.evento_id) if self.evento_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_polygons:
            data["polygons"] = [polygon.to_dict() for polygon in self.polygons]
        return data

    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia del modelo desde un diccionario.
        """
        return cls(
            name=data.get("name"),
            url=data.get("url"),
            width=data.get("width"),
            height=data.get("height"),
            pixels_per_meter=data.get("pixels_per_meter"),
            evento_id=data.get("evento_id"),
        )
