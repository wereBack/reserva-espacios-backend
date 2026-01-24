"""
Modelo para la entidad Zone.
"""

from database import db
from spaces.models.polygon import UUID_TYPE, Polygon


class Zone(Polygon):
    """
    Zona del plano que agrupa espacios y hereda la geometría base de Polygon.
    """

    __tablename__ = "zones"

    id = db.Column(UUID_TYPE, db.ForeignKey("polygons.id"), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    # Relaciones
    spaces = db.relationship("Space", back_populates="zone", lazy=True, foreign_keys="Space.zone_id")

    __mapper_args__ = {
        "polymorphic_identity": "zone",
    }

    def __repr__(self):
        return f"<Zone {self.name}>"

    def to_dict(self):
        """
        Convierte el modelo a diccionario para serialización JSON.
        """
        data = super().to_dict()
        data.update(
            {
                "name": self.name,
                "description": self.description,
                "active": self.active,
                "spaces_count": len(self.spaces) if self.spaces else 0,
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
            description=data.get("description"),
            active=data.get("active", True),
        )
