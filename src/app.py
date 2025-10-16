"""
Aplicación Flask principal para el sistema de reserva de espacios.
"""

from flask import Flask, jsonify
from config import settings
from database import db

# Importar blueprints
from endpoints.health import health_bp

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
        'SQLALCHEMY_DATABASE_URI': config_instance.DATABASE_URL,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ECHO': config_instance.DATABASE_ECHO,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_size': config_instance.DATABASE_POOL_SIZE,
            'max_overflow': config_instance.DATABASE_MAX_OVERFLOW,
        }
    })
    
    # Inicializar extensiones
    db.init_app(app)

    """
    Registrar blueprints
    Te facilito el conceptito de blueprint :)
    https://flask.palletsprojects.com/en/stable/blueprints/ 
    """
    app.register_blueprint(health_bp)
    
    @app.route('/')
    def hello_world():
        """
        Endpoint de prueba.
        
        Returns:
            dict: Mensaje de saludo en formato JSON
        """
        return jsonify({
            'message': 'Hello World!',
            'status': 'success'
        })
    
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

if __name__ == '__main__':
    # Crear aplicación con configuración por defecto
    app = create_app()
    
    # Ejecutar aplicación con configuración de Pydantic
    app.run(
        host=settings.FLASK_HOST,
        port=settings.FLASK_PORT,
        debug=settings.FLASK_DEBUG
    )
