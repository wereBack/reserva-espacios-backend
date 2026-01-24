"""
Modelo para la entidad Polygon.
"""

import uuid
from datetime import UTC, datetime

from database import db

# Intentar importar UUID de PostgreSQL, si no está disponible usar String
try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    UUID_TYPE = PG_UUID(as_uuid=True)
except ImportError:
    UUID_TYPE = db.String(36)


class Polygon(db.Model):
    """
    Clase base polimórfica que representa la forma geométrica asociada
    a zonas y espacios dentro de un plano.
    """

    __tablename__ = "polygons"

    id = db.Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    entity_type = db.Column(db.String(50), nullable=False, default="polygon")
    kind = db.Column(db.String(50), nullable=False)  # Tipo de polígono: "rect", "circle", etc.
    x = db.Column(db.Numeric(10, 6), nullable=False)  # Coordenada X (permite decimales)
    y = db.Column(db.Numeric(10, 6), nullable=False)  # Coordenada Y (permite decimales)
    width = db.Column(db.Numeric(10, 2), nullable=False)  # Ancho
    height = db.Column(db.Numeric(10, 2), nullable=False)  # Alto
    color = db.Column(db.String(7), nullable=False)  # Color en formato hex (#RRGGBB)
    price = db.Column(db.Numeric(10, 2), nullable=True)  # Precio indicado para la figura
    plano_id = db.Column(UUID_TYPE, db.ForeignKey("planos.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relaciones
    plano = db.relationship("Plano", back_populates="polygons", lazy=True)

    __mapper_args__ = {
        "polymorphic_on": entity_type,
        "polymorphic_identity": "polygon",
        "with_polymorphic": "*",
    }

    def __repr__(self):
        return f"<Polygon {self.id} ({self.kind})>"

    def to_dict(self):
        """
        Convierte el modelo a diccionario para serialización JSON.

        Returns:
            dict: Representación del polígono en formato diccionario
        """
        return {
            "id": str(self.id),
            "kind": self.kind,
            "entity_type": self.entity_type,
            "x": float(self.x) if self.x is not None else 0.0,
            "y": float(self.y) if self.y is not None else 0.0,
            "width": float(self.width) if self.width is not None else 0.0,
            "height": float(self.height) if self.height is not None else 0.0,
            "color": self.color,
            "price": float(self.price) if self.price is not None else None,
            "plano_id": str(self.plano_id) if self.plano_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia del modelo desde un diccionario.

        Args:
            data (dict): Datos del polígono

        Returns:
            Polygon: Nueva instancia del modelo
        """
        polygon_id = data.get("id")
        if polygon_id and isinstance(polygon_id, str):
            try:
                polygon_id = uuid.UUID(polygon_id)
            except ValueError:
                polygon_id = uuid.uuid4()
        elif not polygon_id:
            polygon_id = uuid.uuid4()

        return cls(
            id=polygon_id,
            entity_type=data.get("entity_type", "polygon"),
            kind=data.get("kind"),
            x=data.get("x"),
            y=data.get("y"),
            width=data.get("width"),
            height=data.get("height"),
            color=data.get("color"),
            price=data.get("price"),
            plano_id=data.get("plano_id"),
        )
