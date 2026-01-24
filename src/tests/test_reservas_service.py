"""
Tests unitarios para ReservaService.
"""

import uuid
from unittest.mock import patch

from reservas.models.reserva import Reserva
from reservas.service import ReservaService, ReservationStatus


class TestCreateReservation:
    """Tests para ReservaService.create_reservation()"""

    @patch("reservas.service.emit_reservation_created")
    def test_create_reservation_success(self, mock_emit, app, db_session, sample_space):
        """Crear reserva exitosamente en un espacio disponible."""
        with app.app_context():
            # Usar el ID directamente (UUID object) ya que SQLite lo maneja asi
            reserva, error = ReservaService.create_reservation(
                space_id=sample_space.id,
                user_id="user-123",
                asignee="Test User",
            )

            assert error is None
            assert reserva is not None
            assert reserva.estado == ReservationStatus.PENDING
            assert reserva.asignee == "Test User"
            assert reserva.espacio_id == sample_space.id
            mock_emit.assert_called_once()

    def test_create_reservation_space_not_found(self, app, db_session):
        """Error si el espacio no existe."""
        with app.app_context():
            fake_space_id = uuid.uuid4()
            reserva, error = ReservaService.create_reservation(
                space_id=fake_space_id,
                user_id="user-123",
            )

            assert reserva is None
            assert error == "Espacio no encontrado"

    @patch("reservas.service.emit_reservation_created")
    def test_create_reservation_already_pending(self, mock_emit, app, db_session, sample_reserva):
        """Error si ya existe una reserva pendiente para el espacio."""
        with app.app_context():
            # sample_reserva ya tiene estado PENDING
            reserva, error = ReservaService.create_reservation(
                space_id=sample_reserva.espacio_id,
                user_id="otro-user",
            )

            assert reserva is None
            assert "pendiente" in error.lower()

    @patch("reservas.service.emit_reservation_created")
    def test_create_reservation_already_reserved(self, mock_emit, app, db_session, confirmed_reserva):
        """Error si el espacio ya esta reservado."""
        with app.app_context():
            reserva, error = ReservaService.create_reservation(
                space_id=confirmed_reserva.espacio_id,
                user_id="otro-user",
            )

            assert reserva is None
            assert "reservado" in error.lower()


class TestConfirmReservation:
    """Tests para ReservaService.confirm_reservation()"""

    @patch("reservas.service.emit_reservation_updated")
    def test_confirm_reservation_success(self, mock_emit, app, db_session, sample_reserva):
        """Confirmar reserva PENDING exitosamente."""
        with app.app_context():
            reserva, error = ReservaService.confirm_reservation(reservation_id=sample_reserva.id)

            assert error is None
            assert reserva is not None
            assert reserva.estado == ReservationStatus.RESERVED
            mock_emit.assert_called_once()

    def test_confirm_reservation_not_found(self, app, db_session):
        """Error si la reserva no existe."""
        with app.app_context():
            fake_id = uuid.uuid4()
            reserva, error = ReservaService.confirm_reservation(reservation_id=fake_id)

            assert reserva is None
            assert "no encontrada" in error.lower()

    @patch("reservas.service.emit_reservation_updated")
    def test_confirm_reservation_not_pending(self, mock_emit, app, db_session, confirmed_reserva):
        """Error si la reserva no esta en estado PENDING."""
        with app.app_context():
            reserva, error = ReservaService.confirm_reservation(reservation_id=confirmed_reserva.id)

            assert reserva is None
            assert "pendientes" in error.lower()


class TestRejectReservation:
    """Tests para ReservaService.reject_reservation()"""

    @patch("reservas.service.emit_reservation_cancelled")
    def test_reject_reservation_success(self, mock_emit, app, db_session, sample_reserva):
        """Rechazar reserva PENDING exitosamente."""
        with app.app_context():
            reserva, error = ReservaService.reject_reservation(reservation_id=sample_reserva.id)

            assert error is None
            assert reserva is not None
            assert reserva.estado == ReservationStatus.CANCELLED
            mock_emit.assert_called_once()

    def test_reject_reservation_not_found(self, app, db_session):
        """Error si la reserva no existe."""
        with app.app_context():
            fake_id = uuid.uuid4()
            reserva, error = ReservaService.reject_reservation(reservation_id=fake_id)

            assert reserva is None
            assert "no encontrada" in error.lower()

    @patch("reservas.service.emit_reservation_cancelled")
    def test_reject_reservation_not_pending(self, mock_emit, app, db_session, confirmed_reserva):
        """Error si la reserva no esta en estado PENDING."""
        with app.app_context():
            reserva, error = ReservaService.reject_reservation(reservation_id=confirmed_reserva.id)

            assert reserva is None
            assert "pendientes" in error.lower()


class TestCancelReservation:
    """Tests para ReservaService.cancel_reservation()"""

    @patch("reservas.service.emit_reservation_cancelled")
    def test_cancel_pending_reservation(self, mock_emit, app, db_session, sample_reserva):
        """Cancelar reserva PENDING exitosamente."""
        with app.app_context():
            reserva, error = ReservaService.cancel_reservation(reservation_id=sample_reserva.id)

            assert error is None
            assert reserva is not None
            assert reserva.estado == ReservationStatus.CANCELLED
            mock_emit.assert_called_once()

    @patch("reservas.service.emit_reservation_cancelled")
    def test_cancel_confirmed_reservation(self, mock_emit, app, db_session, confirmed_reserva):
        """Cancelar reserva RESERVED exitosamente."""
        with app.app_context():
            reserva, error = ReservaService.cancel_reservation(reservation_id=confirmed_reserva.id)

            assert error is None
            assert reserva is not None
            assert reserva.estado == ReservationStatus.CANCELLED

    def test_cancel_reservation_not_found(self, app, db_session):
        """Error si la reserva no existe."""
        with app.app_context():
            fake_id = uuid.uuid4()
            reserva, error = ReservaService.cancel_reservation(reservation_id=fake_id)

            assert reserva is None
            assert "no encontrada" in error.lower()

    def test_cancel_already_cancelled_reservation(self, app, db_session, sample_space):
        """Error si la reserva ya esta cancelada."""
        with app.app_context():
            # Crear reserva cancelada
            cancelled_reserva = Reserva(
                id=uuid.uuid4(),
                espacio_id=sample_space.id,
                estado=ReservationStatus.CANCELLED,
            )
            db_session.add(cancelled_reserva)
            db_session.commit()

            reserva, error = ReservaService.cancel_reservation(reservation_id=cancelled_reserva.id)

            assert reserva is None
            assert "no est" in error.lower()


class TestGetReservations:
    """Tests para metodos de consulta de reservas."""

    def test_get_reservation_by_id(self, app, db_session, sample_reserva):
        """Obtener reserva por ID."""
        with app.app_context():
            reserva = ReservaService.get_reservation_by_id(sample_reserva.id)

            assert reserva is not None
            assert reserva.id == sample_reserva.id

    def test_get_reservation_by_id_not_found(self, app, db_session):
        """Retorna None si la reserva no existe."""
        with app.app_context():
            reserva = ReservaService.get_reservation_by_id(uuid.uuid4())

            assert reserva is None

    def test_get_reservations_by_space(self, app, db_session, sample_reserva):
        """Obtener todas las reservas de un espacio."""
        with app.app_context():
            reservas = ReservaService.get_reservations_by_space(sample_reserva.espacio_id)

            assert len(reservas) == 1
            assert reservas[0].id == sample_reserva.id

    def test_get_active_reservation_by_space(self, app, db_session, sample_reserva):
        """Obtener reserva activa de un espacio."""
        with app.app_context():
            reserva = ReservaService.get_active_reservation_by_space(sample_reserva.espacio_id)

            assert reserva is not None
            assert reserva.id == sample_reserva.id

    def test_get_active_reservation_by_space_none(self, app, db_session, sample_space):
        """Retorna None si no hay reserva activa."""
        with app.app_context():
            reserva = ReservaService.get_active_reservation_by_space(sample_space.id)

            assert reserva is None

    def test_get_pending_reservations(self, app, db_session, sample_reserva):
        """Obtener todas las reservas pendientes."""
        with app.app_context():
            pending = ReservaService.get_pending_reservations()

            assert len(pending) == 1
            assert pending[0].estado == ReservationStatus.PENDING


class TestGetReservationStatus:
    """Tests para ReservaService.get_reservation_status()"""

    def test_get_status_existing_reservation(self, app, db_session, sample_reserva):
        """Obtener estado de reserva existente."""
        with app.app_context():
            status = ReservaService.get_reservation_status(sample_reserva.id)

            assert status is not None
            assert status["exists_in_database"] is True
            assert status["reservation"] is not None
            assert status["reservation"]["estado"] == "PENDING"

    def test_get_status_non_existing_reservation(self, app, db_session):
        """Obtener estado de reserva inexistente."""
        with app.app_context():
            status = ReservaService.get_reservation_status(uuid.uuid4())

            assert status is not None
            assert status["exists_in_database"] is False
            assert status["reservation"] is None
