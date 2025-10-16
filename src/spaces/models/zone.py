"""
Modelo para la entidad Zone.
"""

from datetime import datetime, timezone
from database import db


class Zone(db.Model):
    """
    Modelo que representa una zona donde se ubican los espacios.
    """
    __tablename__ = 'zones'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), nullable=True)  # Color en formato hex (#RRGGBB)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)  # Precio base para la zona
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relaciones
    spaces = db.relationship('Space', backref='zone', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Zone {self.name}>'
    
    def to_dict(self):
        """
        Convierte el modelo a diccionario para serialización JSON.
        
        Returns:
            dict: Representación de la zona en formato diccionario
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'price': float(self.price) if self.price else 0.0,
            'active': self.active,
            'spaces_count': len(self.spaces) if self.spaces else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia del modelo desde un diccionario.
        
        Args:
            data (dict): Datos de la zona
            
        Returns:
            Zone: Nueva instancia del modelo
        """
        return cls(
            name=data.get('name'),
            description=data.get('description'),
            color=data.get('color'),
            price=data.get('price', 0.0),
            active=data.get('active', True)
        )
    
    def get_spaces_count(self):
        """
        Obtiene el número de espacios en esta zona.
        
        Returns:
            int: Número de espacios
        """
        return len(self.spaces) if self.spaces else 0
    
    def get_active_spaces_count(self):
        """
        Obtiene el número de espacios activos en esta zona.
        
        Returns:
            int: Número de espacios activos
        """
        if not self.spaces:
            return 0
        return sum(1 for space in self.spaces if space.active)
    
    def set_color(self, color):
        """
        Establece el color de la zona.
        
        Args:
            color (str): Color en formato hex (#RRGGBB)
        """
        if color and not color.startswith('#'):
            color = f"#{color}"
        self.color = color
