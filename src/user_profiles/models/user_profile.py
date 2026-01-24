"""
Modelo para el perfil de usuario.
"""

import uuid
from datetime import UTC, datetime

from database import db

try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    UUID_TYPE = PG_UUID(as_uuid=True)
except ImportError:
    UUID_TYPE = db.String(36)


class UserProfile(db.Model):
    """
    Perfil de usuario con datos de contacto.
    Se asocia al user_id del token de Keycloak.
    """

    __tablename__ = "user_profiles"

    id = db.Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # Datos de contacto
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    linkedin = db.Column(db.String(255), nullable=True)

    # Datos de empresa
    company = db.Column(db.String(255), nullable=True)
    position = db.Column(db.String(255), nullable=True)

    # Notas adicionales
    notes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self):
        return f"<UserProfile {self.id} user_id={self.user_id}>"

    def to_dict(self):
        """
        Convierte el modelo a diccionario para serialización JSON.
        """
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "email": self.email,
            "phone": self.phone,
            "linkedin": self.linkedin,
            "company": self.company,
            "position": self.position,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_complete(self):
        """
        Verifica si el perfil tiene los campos mínimos requeridos.
        Por ahora solo se requiere email.
        """
        return bool(self.email and self.email.strip())

    @classmethod
    def from_dict(cls, data, user_id):
        """
        Crea una instancia de UserProfile desde un diccionario.
        """
        return cls(
            user_id=user_id,
            email=data.get("email"),
            phone=data.get("phone"),
            linkedin=data.get("linkedin"),
            company=data.get("company"),
            position=data.get("position"),
            notes=data.get("notes"),
        )
