"""
Endpoints de verificación de salud del servicio.
"""

from flask import Blueprint, jsonify

# Blueprint para endpoints de espacios
spaces_bp = Blueprint("spaces", __name__, url_prefix="/spaces")

@spaces_bp.route("/", methods=["GET"])
def get_spaces():
    """Handler principal del endpoint /spaces."""
    return jsonify({"message": "Hello World!", "status": "success"}), 200
