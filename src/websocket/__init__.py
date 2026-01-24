"""
Módulo de WebSocket para notificaciones en tiempo real.
"""

from websocket.socket_manager import init_socketio, socketio

__all__ = ["socketio", "init_socketio"]
