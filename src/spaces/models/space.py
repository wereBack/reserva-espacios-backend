"""
Modelo para la entidad Espacio.
"""

from database import db
from spaces.models.polygon import UUID_TYPE, Polygon


class Space(Polygon):
    """
    Espacio reservable dentro de un plano, asociado opcionalmente a una zona.
    """

    __tablename__ = "spaces"

    id = db.Column(UUID_TYPE, db.ForeignKey("polygons.id"), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    zone_id = db.Column(UUID_TYPE, db.ForeignKey("zones.id"), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    # Relaciones
    zone = db.relationship("Zone", back_populates="spaces", lazy=True, foreign_keys=[zone_id])
    reservations = db.relationship(
        "Reserva",
        back_populates="space",
        lazy=True,
        cascade="all, delete-orphan",
    )

    __mapper_args__ = {
        "polymorphic_identity": "space",
    }

    def __repr__(self):
        return f"<Space {self.name}>"

    def to_dict(self):
        """
        Convierte el modelo a diccionario para serialización JSON.
        """
        data = super().to_dict()
        data.update(
            {
                "name": self.name,
                "zone_id": str(self.zone_id) if self.zone_id else None,
                "active": self.active,
                "reservations": [reservation.to_dict() for reservation in self.reservations],
            }
        )
        return data

    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia del modelo desde un diccionario.
        """
        return cls(
            kind=data.get("kind"),
            x=data.get("x"),
            y=data.get("y"),
            width=data.get("width"),
            height=data.get("height"),
            color=data.get("color"),
            rotation=data.get("rotation", 0),
            price=data.get("price"),
            plano_id=data.get("plano_id"),
            name=data.get("name"),
            zone_id=data.get("zone_id"),
            active=data.get("active", True),
        )
