"""
Aplicación Flask principal para el sistema de reserva de espacios.
"""

from flask import Flask, jsonify
from flask_cors import CORS
from config import settings
from database import db

# Importo blueprints
from health.routes import health_bp
from spaces.routes import spaces_bp, zones_bp
from eventos.routes import eventos_bp
from planos.routes import planos_bp
from reservas.routes import reservas_bp

# Importo modelos sin blueprint para que SQLAlchemy los registre
from reservas.models.reserva import Reserva  # noqa: F401

# Importo WebSocket
from websocket import socketio, init_socketio

# Variable global para el listener de Redis
_expiration_listener = None


def create_app(config_instance=None):
    """
    Factory function para crear la aplicación Flask.
    
    Args:
        config_instance: Instancia de configuración Pydantic a utilizar.
                        Si no se proporciona, se usa la configuración por defecto.
        
    Returns:
        Flask: Instancia de la aplicación Flask configurada
    """
    if config_instance is None:
        config_instance = settings
    
    app = Flask(__name__)
    
    # Configurar Flask con los valores de Pydantic
    app.config.update({
        'SECRET_KEY': config_instance.FLASK_SECRET_KEY,
        'DEBUG': config_instance.FLASK_DEBUG,
        'HOST': config_instance.FLASK_HOST,
        'PORT': config_instance.FLASK_PORT,
        'LOG_LEVEL': config_instance.FLASK_LOG_LEVEL,
        # Configuración de base de datos
        'SQLALCHEMY_DATABASE_URI': str(config_instance.DATABASE_URL),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ECHO': config_instance.DATABASE_ECHO,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_size': config_instance.DATABASE_POOL_SIZE,
            'max_overflow': config_instance.DATABASE_MAX_OVERFLOW,
        }
    })
    
    # Inicializar extensiones
    db.init_app(app)
    CORS(app)
    
    # Inicializar WebSocket
    init_socketio(app)

    """
    Registro de blueprints
    Te facilito el conceptito de blueprint :)
    https://flask.palletsprojects.com/en/stable/blueprints/ 
    """
    app.register_blueprint(health_bp)
    app.register_blueprint(spaces_bp)
    app.register_blueprint(zones_bp)
    app.register_blueprint(eventos_bp)
    app.register_blueprint(planos_bp)
    app.register_blueprint(reservas_bp)
    
    @app.errorhandler(404)
    def not_found(error):
        """
        Manejador de errores para rutas no encontradas.
        
        Args:
            error: Error 404
            
        Returns:
            dict: Mensaje de error en formato JSON
        """
        return jsonify({
            'error': 'Endpoint no encontrado',
            'status': 'error',
            'code': 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """
        Manejador de errores para errores internos del servidor.
        
        Args:
            error: Error 500
            
        Returns:
            dict: Mensaje de error en formato JSON
        """
        return jsonify({
            'error': 'Error interno del servidor',
            'status': 'error',
            'code': 500
        }), 500
    
    return app


def start_expiration_listener(app):
    """
    Inicia el listener de expiración de Redis.
    Debe llamarse después de crear la aplicación.
    
    Args:
        app: Aplicación Flask
    """
    global _expiration_listener
    
    from redis_client import RedisExpirationListener
    from reservas.service import ReservaService
    
    def on_reservation_expired(reservation_id: str):
        """Callback cuando una reserva expira en Redis."""
        with app.app_context():
            ReservaService.process_expired_reservation(reservation_id)
    
    _expiration_listener = RedisExpirationListener(on_reservation_expired)
    _expiration_listener.start()


def stop_expiration_listener():
    """Detiene el listener de expiración de Redis."""
    global _expiration_listener
    
    if _expiration_listener:
        _expiration_listener.stop()
        _expiration_listener = None


if __name__ == '__main__':
    # Importar eventlet y hacer monkey patching antes de todo
    import eventlet
    eventlet.monkey_patch()
    
    # Crear aplicación con configuración por defecto
    app = create_app()
    
    # Iniciar listener de expiración de Redis
    start_expiration_listener(app)
    
    try:
        # Ejecutar aplicación con SocketIO
        socketio.run(
            app,
            host=settings.FLASK_HOST,
            port=settings.FLASK_PORT,
            debug=settings.FLASK_DEBUG
        )
    finally:
        stop_expiration_listener()
