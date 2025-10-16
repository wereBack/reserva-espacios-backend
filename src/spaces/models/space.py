"""
Modelo para la entidad Espacio.
"""

from datetime import datetime, timezone
from database import db


class Space(db.Model):
    """
    Modelo que representa un espacio físico disponible para reservar.
    """
    __tablename__ = 'spaces'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    size_px = db.Column(db.String(20), nullable=False)  # Format: "widthxheight" example: "100x200"
    x_coordinate = db.Column(db.Integer, nullable=False, default=0)
    y_coordinate = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relaciones
    zone = db.relationship('Zone', backref='spaces', lazy=True)
    reservations = db.relationship('Reservation', backref='space', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Space {self.name}>'
    
    def get_size_dimensions(self):
        """
        Obtiene las dimensiones del espacio en píxeles.
        
        Returns:
            tuple: (ancho, alto) en píxeles
        """
        if not self.size_px or 'x' not in self.size_px:
            return (0, 0)
        
        try:
            width, height = self.size_px.split('x')
            return (int(width), int(height))
        except (ValueError, IndexError):
            return (0, 0)
    
    def set_size_dimensions(self, width, height):
        """
        Establece las dimensiones del espacio en píxeles.
        
        Args:
            width (int): Ancho en píxeles
            height (int): Alto en píxeles
        """
        self.size_px = f"{width}x{height}"
    
    def get_coordinates(self):
        """
        Obtiene las coordenadas del espacio.
        
        Returns:
            tuple: (x, y) coordenadas
        """
        return (self.x_coordinate, self.y_coordinate)
    
    def set_coordinates(self, x, y):
        """
        Establece las coordenadas del espacio.
        
        Args:
            x (int): Coordenada X
            y (int): Coordenada Y
        """
        self.x_coordinate = x
        self.y_coordinate = y
    
    def to_dict(self):
        """
        Convierte el modelo a diccionario para serialización JSON.
        
        Returns:
            dict: Representación del espacio en formato diccionario
        """
        return {
            'id': self.id,
            'name': self.name,
            'zone_id': self.zone_id,
            'price': float(self.price) if self.price else 0.0,
            'size_px': self.size_px,
            'x_coordinate': self.x_coordinate,
            'y_coordinate': self.y_coordinate,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia del modelo desde un diccionario.
        
        Args:
            data (dict): Datos del espacio
            
        Returns:
            Space: Nueva instancia del modelo
        """
        return cls(
            name=data.get('name'),
            zone_id=data.get('zone_id'),
            price=data.get('price', 0.0),
            size_px=data.get('size_px'),
            x_coordinate=data.get('x_coordinate', 0),
            y_coordinate=data.get('y_coordinate', 0),
            active=data.get('active', True)
        )
