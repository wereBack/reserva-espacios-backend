"""
Modelo para la entidad Setting.
"""

import uuid
from datetime import datetime, timezone

from database import db

try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    UUID_TYPE = PG_UUID(as_uuid=True)
except ImportError:
    UUID_TYPE = db.String(36)


class Setting(db.Model):
    """
    Configuración general del sistema (banderas, URLs y nombres).
    """

    __tablename__ = 'settings'

    id = db.Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    pagina_prendida = db.Column(db.Boolean, nullable=False, default=False)
    url = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f'<Setting {self.name}>'

    def to_dict(self):
        """
        Convierte el modelo a diccionario para serialización JSON.
        """
        return {
            'id': str(self.id),
            'pagina_prendida': self.pagina_prendida,
            'url': self.url,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia del modelo desde un diccionario.
        """
        return cls(
            pagina_prendida=data.get('pagina_prendida', False),
            url=data.get('url'),
            name=data.get('name'),
        )

