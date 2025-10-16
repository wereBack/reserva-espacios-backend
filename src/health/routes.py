"""
Endpoints de verificación de salud del servicio.
"""

from datetime import datetime, timezone
from flask import Blueprint, jsonify
from utils.db_utils import check_database_connection

# Blueprint para health checks
health_bp = Blueprint("health", __name__, url_prefix="/health")

@health_bp.route("/")
def health_check():
    """Handler principal del endpoint /health."""
    db_status = check_database_connection()
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
