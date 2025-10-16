"""
Endpoints de verificación de salud del servicio.
"""

from datetime import datetime, timezone
from flask import Blueprint, jsonify, current_app
from sqlalchemy import text

# Blueprint para health checks
health_bp = Blueprint("health", __name__, url_prefix="/health")

def get_db():
    """Obtengo la instancia de SQLAlchemy desde la app actual."""
    return current_app.extensions["sqlalchemy"]

def check_database_health() -> dict:
    """Verifico la conexión con la base de datos."""
    db = get_db()
    try:
        db.session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "message": "Base de datos conectada correctamente",
            "ok": True,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Base de datos no conectada: {e}",
            "ok": False,
        }

@health_bp.route("/")
def health_check():
    """Handler principal del endpoint /health."""
    db_status = check_database_health()
    healthy = db_status["ok"]
    
    status = "healthy" if healthy else "unhealthy"
    message = "Servicio funcionando correctamente" if healthy else "Servicio con problemas de conectividad"

    response = {
        "status": status,
        "message": message,
        "uptime": "running",
        "database": {
            "status": db_status["status"],
            "message": db_status["message"],
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    return jsonify(response), 200 if healthy else 503
