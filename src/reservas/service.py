"""
Servicio de reservas con integración WebSocket.

Flujo de reservas:
1. Usuario solicita reserva -> estado PENDING
2. Admin confirma -> estado RESERVED
3. Admin rechaza -> estado CANCELLED
"""

import logging
from typing import Optional, Tuple

from database import db
from reservas.models.reserva import Reserva
from spaces.models.space import Space
from websocket.socket_manager import (
    emit_reservation_created,
    emit_reservation_updated,
    emit_reservation_expired,
    emit_reservation_cancelled,
    emit_cancellation_requested,
)

logger = logging.getLogger(__name__)


class ReservationStatus:
    """Estados posibles de una reserva."""
    PENDING = "PENDING"      # Esperando confirmación del admin
    RESERVED = "RESERVED"    # Confirmada por admin
    EXPIRED = "EXPIRED"      # Expiró sin confirmar
    CANCELLED = "CANCELLED"  # Cancelada


class ReservaService:
    """
    Servicio para gestionar reservas.
    Integra PostgreSQL (persistencia) y WebSocket (notificaciones).
    """
    
    @classmethod
    def create_reservation(
        cls,
        space_id: str,
        user_id: Optional[str] = None,
        asignee: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ) -> Tuple[Optional[Reserva], Optional[str]]:
        """
        Crea una nueva reserva en estado PENDING.
        El admin debe confirmar la reserva manualmente.
        
        1. Verifica que el espacio exista y esté disponible
        2. Guarda la reserva en PostgreSQL con estado PENDING
        3. Emite evento WebSocket
        
        Args:
            space_id: ID del espacio a reservar
            user_id: ID del usuario (de Keycloak)
            asignee: Nombre del asignado
            ttl_seconds: No usado actualmente
            
        Returns:
            Tuple[Reserva, None] si éxito, Tuple[None, error_message] si falla
        """
        try:
            # Verificar que el espacio exista
            space = Space.query.get(space_id)
            if not space:
                return None, "Espacio no encontrado"
            
            # Verificar que no haya una reserva activa (PENDING o RESERVED) para ese espacio
            existing = Reserva.query.filter(
                Reserva.espacio_id == space_id,
                Reserva.estado.in_([ReservationStatus.PENDING, ReservationStatus.RESERVED])
            ).first()
            
            if existing:
                if existing.estado == ReservationStatus.PENDING:
                    return None, "El espacio ya tiene una reserva pendiente de confirmación"
                return None, "El espacio ya está reservado"
            
            # Crear reserva en BD como PENDING (sin expiración)
            reserva = Reserva(
                espacio_id=space_id,
                user_id=user_id,
                asignee=asignee,
                estado=ReservationStatus.PENDING,
                expires_at=None,
            )
            
            db.session.add(reserva)
            db.session.commit()
            
            # Obtener plano_id para el WebSocket
            plano_id = str(space.plano_id) if space.plano_id else None
            
            # Emitir evento WebSocket
            emit_reservation_created(reserva.to_dict(), plano_id)
            
            logger.info(f"Reserva {reserva.id} creada como PENDING para espacio {space_id}")
            
            return reserva, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creando reserva: {e}")
            return None, str(e)
    
    @classmethod
    def confirm_reservation(cls, reservation_id: str) -> Tuple[Optional[Reserva], Optional[str]]:
        """
        Confirma una reserva pendiente (PENDING -> RESERVED).
        Solo puede ser llamado por un admin.
        
        Args:
            reservation_id: ID de la reserva a confirmar
            
        Returns:
            Tuple[Reserva, None] si éxito, Tuple[None, error_message] si falla
        """
        try:
            reserva = Reserva.query.get(reservation_id)
            if not reserva:
                return None, "Reserva no encontrada"
            
            if reserva.estado != ReservationStatus.PENDING:
                return None, f"Solo se pueden confirmar reservas pendientes (estado actual: {reserva.estado})"
            
            # Actualizar estado en BD a RESERVED
            reserva.estado = ReservationStatus.RESERVED
            db.session.commit()
            
            # Obtener plano_id para el WebSocket
            space = Space.query.get(reserva.espacio_id)
            plano_id = str(space.plano_id) if space and space.plano_id else None
            
            # Emitir evento WebSocket
            emit_reservation_updated(reserva.to_dict(), plano_id)
            
            logger.info(f"Reserva {reservation_id} confirmada por admin")
            
            return reserva, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error confirmando reserva: {e}")
            return None, str(e)
    
    @classmethod
    def reject_reservation(cls, reservation_id: str) -> Tuple[Optional[Reserva], Optional[str]]:
        """
        Rechaza una reserva pendiente (PENDING -> CANCELLED).
        Solo puede ser llamado por un admin.
        
        Args:
            reservation_id: ID de la reserva a rechazar
            
        Returns:
            Tuple[Reserva, None] si éxito, Tuple[None, error_message] si falla
        """
        try:
            reserva = Reserva.query.get(reservation_id)
            if not reserva:
                return None, "Reserva no encontrada"
            
            if reserva.estado != ReservationStatus.PENDING:
                return None, f"Solo se pueden rechazar reservas pendientes (estado actual: {reserva.estado})"
            
            # Actualizar estado en BD
            reserva.estado = ReservationStatus.CANCELLED
            db.session.commit()
            
            # Obtener plano_id para el WebSocket
            space = Space.query.get(reserva.espacio_id)
            plano_id = str(space.plano_id) if space and space.plano_id else None
            
            # Emitir evento WebSocket
            emit_reservation_cancelled(reserva.to_dict(), plano_id)
            
            logger.info(f"Reserva {reservation_id} rechazada por admin")
            
            return reserva, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error rechazando reserva: {e}")
            return None, str(e)
    
    @classmethod
    def cancel_reservation(cls, reservation_id: str) -> Tuple[Optional[Reserva], Optional[str]]:
        """
        Cancela una reserva (PENDING o RESERVED -> CANCELLED).
        
        Args:
            reservation_id: ID de la reserva a cancelar
            
        Returns:
            Tuple[Reserva, None] si éxito, Tuple[None, error_message] si falla
        """
        try:
            reserva = Reserva.query.get(reservation_id)
            if not reserva:
                return None, "Reserva no encontrada"
            
            if reserva.estado not in [ReservationStatus.PENDING, ReservationStatus.RESERVED]:
                return None, f"La reserva no está activa (estado: {reserva.estado})"
            
            # Actualizar estado en BD
            reserva.estado = ReservationStatus.CANCELLED
            db.session.commit()
            
            # Obtener plano_id para el WebSocket
            space = Space.query.get(reserva.espacio_id)
            plano_id = str(space.plano_id) if space and space.plano_id else None
            
            # Emitir evento WebSocket
            emit_reservation_cancelled(reserva.to_dict(), plano_id)
            
            logger.info(f"Reserva {reservation_id} cancelada")
            
            return reserva, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cancelando reserva: {e}")
            return None, str(e)
    
    @classmethod
    def get_reservation_status(cls, reservation_id: str) -> Optional[dict]:
        """
        Obtiene el estado detallado de una reserva.
        
        Returns:
            dict con:
            - exists_in_database: bool
            - reservation: dict o None
        """
        try:
            reserva = Reserva.query.get(reservation_id)
            
            return {
                'exists_in_database': reserva is not None,
                'reservation': reserva.to_dict() if reserva else None,
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de reserva: {e}")
            return None
    
    @classmethod
    def get_reservation_by_id(cls, reservation_id: str) -> Optional[Reserva]:
        """
        Obtiene una reserva por su ID.
        
        Args:
            reservation_id: ID de la reserva
            
        Returns:
            Reserva o None
        """
        return Reserva.query.get(reservation_id)
    
    @classmethod
    def get_reservations_by_space(cls, space_id: str) -> list:
        """
        Obtiene todas las reservas de un espacio.
        
        Args:
            space_id: ID del espacio
            
        Returns:
            Lista de reservas
        """
        return Reserva.query.filter_by(espacio_id=space_id).all()
    
    @classmethod
    def get_active_reservation_by_space(cls, space_id: str) -> Optional[Reserva]:
        """
        Obtiene la reserva activa de un espacio si existe.
        Incluye tanto PENDING como RESERVED.
        
        Args:
            space_id: ID del espacio
            
        Returns:
            Reserva activa o None
        """
        return Reserva.query.filter(
            Reserva.espacio_id == space_id,
            Reserva.estado.in_([ReservationStatus.PENDING, ReservationStatus.RESERVED])
        ).first()
    
    @classmethod
    def get_pending_reservations(cls) -> list:
        """
        Obtiene todas las reservas pendientes de confirmación.
        Para uso del panel de admin.
        
        Returns:
            Lista de reservas pendientes
        """
        return Reserva.query.filter_by(estado=ReservationStatus.PENDING).all()
    
    @classmethod
    def get_reservations_by_user(cls, user_id: str) -> list:
        """
        Obtiene todas las reservas de un usuario específico.
        Incluye reservas activas y el historial reciente.
        
        Args:
            user_id: ID del usuario (de Keycloak)
            
        Returns:
            Lista de reservas del usuario
        """
        return Reserva.query.filter_by(user_id=user_id).order_by(Reserva.created_at.desc()).all()
    
    @classmethod
    def request_cancellation(cls, reservation_id: str, user_id: str) -> Tuple[Optional[Reserva], Optional[str]]:
        """
        Solicita la cancelación de una reserva confirmada.
        Cambia el estado a CANCELLATION_REQUESTED para que el admin lo revise.
        
        Args:
            reservation_id: ID de la reserva
            user_id: ID del usuario que solicita la cancelación
            
        Returns:
            Tuple[Reserva, None] si éxito, Tuple[None, error_message] si falla
        """
        try:
            reserva = Reserva.query.get(reservation_id)
            if not reserva:
                return None, "Reserva no encontrada"
            
            # Verificar que la reserva pertenezca al usuario
            if reserva.user_id != user_id:
                return None, "No tienes permiso para cancelar esta reserva"
            
            if reserva.estado == ReservationStatus.PENDING:
                # Si está pendiente, cancelar directamente
                reserva.estado = ReservationStatus.CANCELLED
                db.session.commit()
                
                # Obtener plano_id para el WebSocket
                space = Space.query.get(reserva.espacio_id)
                plano_id = str(space.plano_id) if space and space.plano_id else None
                
                emit_reservation_cancelled(reserva.to_dict(), plano_id)
                logger.info(f"Reserva {reservation_id} cancelada por usuario")
                return reserva, None
                
            elif reserva.estado == ReservationStatus.RESERVED:
                # Si está confirmada, marcar como solicitud de cancelación
                reserva.estado = "CANCELLATION_REQUESTED"
                db.session.commit()
                
                # Obtener plano_id para el WebSocket
                space = Space.query.get(reserva.espacio_id)
                plano_id = str(space.plano_id) if space and space.plano_id else None
                
                emit_cancellation_requested(reserva.to_dict(), plano_id)
                logger.info(f"Solicitud de cancelación para reserva {reservation_id}")
                return reserva, None
            else:
                return None, f"La reserva no está activa (estado: {reserva.estado})"
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error solicitando cancelación: {e}")
            return None, str(e)    
