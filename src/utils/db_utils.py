"""
Utilidades para la base de datos.
"""

from flask import current_app
from sqlalchemy import text


def get_db():
    """
    Obtiene la instancia de SQLAlchemy desde la app actual.

    Returns:
        SQLAlchemy: Instancia de SQLAlchemy
    """
    return current_app.extensions["sqlalchemy"]


def execute_query(query, params=None):
    """
    Ejecuta una consulta SQL de forma segura.

    Args:
        query (str): Consulta SQL
        params (dict): Parámetros para la consulta

    Returns:
        Result: Resultado de la consulta
    """
    db = get_db()
    return db.session.execute(text(query), params or {})


def check_database_connection():
    """
    Verifica la conexión con la base de datos.

    Returns:
        dict: Estado de la conexión
    """
    try:
        execute_query("SELECT 1")
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


def get_database_info():
    """
    Obtiene información sobre la base de datos.

    Returns:
        dict: Información de la base de datos
    """
    try:
        db = get_db()
        return {
            "url": str(db.engine.url),
            "echo": db.engine.echo,
            "pool_size": db.engine.pool.size(),
            "checked_out": db.engine.pool.checkedout(),
            "overflow": db.engine.pool.overflow(),
        }
    except Exception as e:
        return {"error": f"Error obteniendo información de la base de datos: {e}"}


def init_database():
    """
    Inicializa la base de datos creando todas las tablas.
    """
    db = get_db()
    db.create_all()


def drop_database():
    """
    Elimina todas las tablas de la base de datos.
    """
    db = get_db()
    db.drop_all()
