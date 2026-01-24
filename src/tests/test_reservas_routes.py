"""
Tests de integracion para endpoints REST de reservas.
Usa mocks del servicio para evitar problemas con SQLite/UUID.
"""

import json
import uuid
from unittest.mock import MagicMock, patch


class TestCreateReservationEndpoint:
    """Tests para POST /api/reservas"""

    @patch("user_profiles.models.user_profile.UserProfile")
    @patch("reservas.routes.ReservaService")
    def test_create_reservation_authenticated(self, mock_service, mock_user_profile, client, auth_headers):
        """Usuario autenticado puede crear reserva."""
        # Mock del perfil de usuario completo
        mock_profile = MagicMock()
        mock_profile.is_complete.return_value = True
        mock_user_profile.query.filter_by.return_value.first.return_value = mock_profile

        # Configurar mock del servicio
        mock_reserva = MagicMock()
        mock_reserva.to_dict.return_value = {
            "id": str(uuid.uuid4()),
            "estado": "PENDING",
            "space_id": str(uuid.uuid4()),
        }
        mock_service.create_reservation.return_value = (mock_reserva, None)

        response = client.post(
            "/api/reservas",
            headers=auth_headers,
            data=json.dumps({"space_id": str(uuid.uuid4())}),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "success"
        assert data["reservation"]["estado"] == "PENDING"

    def test_create_reservation_unauthenticated(self, client):
        """Usuario no autenticado no puede crear reserva."""
        response = client.post(
            "/api/reservas",
            data=json.dumps({"space_id": str(uuid.uuid4())}),
            content_type="application/json",
        )

        assert response.status_code == 401

    def test_create_reservation_invalid_token(self, client, invalid_auth_headers):
        """Token invalido rechazado."""
        response = client.post(
            "/api/reservas",
            headers=invalid_auth_headers,
            data=json.dumps({"space_id": str(uuid.uuid4())}),
            content_type="application/json",
        )

        assert response.status_code == 401

    def test_create_reservation_missing_space_id(self, client, auth_headers):
        """Error si falta space_id."""
        response = client.post(
            "/api/reservas",
            headers=auth_headers,
            data=json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "space_id" in data["error"].lower()

    @patch("user_profiles.models.user_profile.UserProfile")
    @patch("reservas.routes.ReservaService")
    def test_create_reservation_space_not_found(self, mock_service, mock_user_profile, client, auth_headers):
        """Error si el espacio no existe."""
        # Mock del perfil de usuario completo
        mock_profile = MagicMock()
        mock_profile.is_complete.return_value = True
        mock_user_profile.query.filter_by.return_value.first.return_value = mock_profile

        mock_service.create_reservation.return_value = (None, "Espacio no encontrado")

        response = client.post(
            "/api/reservas",
            headers=auth_headers,
            data=json.dumps({"space_id": str(uuid.uuid4())}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "no encontrado" in data["error"].lower()


class TestGetReservationEndpoint:
    """Tests para GET /api/reservas/<id>"""

    @patch("reservas.routes.ReservaService")
    def test_get_reservation_exists(self, mock_service, client):
        """Obtener reserva existente."""
        reservation_id = str(uuid.uuid4())
        mock_reserva = MagicMock()
        mock_reserva.to_dict.return_value = {
            "id": reservation_id,
            "estado": "PENDING",
        }
        mock_service.get_reservation_by_id.return_value = mock_reserva

        response = client.get(f"/api/reservas/{reservation_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["reservation"]["id"] == reservation_id

    @patch("reservas.routes.ReservaService")
    def test_get_reservation_not_found(self, mock_service, client):
        """Error 404 si la reserva no existe."""
        mock_service.get_reservation_by_id.return_value = None

        response = client.get(f"/api/reservas/{uuid.uuid4()}")

        assert response.status_code == 404


class TestCancelReservationEndpoint:
    """Tests para DELETE /api/reservas/<id>"""

    @patch("reservas.routes.ReservaService")
    def test_cancel_reservation_authenticated(self, mock_service, client, auth_headers):
        """Usuario autenticado puede cancelar reserva."""
        reservation_id = str(uuid.uuid4())
        mock_reserva = MagicMock()
        mock_reserva.to_dict.return_value = {
            "id": reservation_id,
            "estado": "CANCELLED",
        }
        mock_service.cancel_reservation.return_value = (mock_reserva, None)

        response = client.delete(
            f"/api/reservas/{reservation_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["reservation"]["estado"] == "CANCELLED"

    def test_cancel_reservation_unauthenticated(self, client):
        """Usuario no autenticado no puede cancelar."""
        response = client.delete(f"/api/reservas/{uuid.uuid4()}")

        assert response.status_code == 401


class TestGetReservationsBySpaceEndpoint:
    """Tests para GET /api/reservas/space/<space_id>"""

    @patch("reservas.routes.ReservaService")
    def test_get_reservations_by_space(self, mock_service, client):
        """Obtener reservas de un espacio."""
        mock_reserva = MagicMock()
        mock_reserva.to_dict.return_value = {"id": str(uuid.uuid4()), "estado": "PENDING"}
        mock_service.get_reservations_by_space.return_value = [mock_reserva]

        response = client.get(f"/api/reservas/space/{uuid.uuid4()}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert len(data["reservations"]) == 1

    @patch("reservas.routes.ReservaService")
    def test_get_reservations_by_space_empty(self, mock_service, client):
        """Lista vacia si no hay reservas."""
        mock_service.get_reservations_by_space.return_value = []

        response = client.get(f"/api/reservas/space/{uuid.uuid4()}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["reservations"] == []


class TestGetActiveReservationBySpaceEndpoint:
    """Tests para GET /api/reservas/space/<space_id>/active"""

    @patch("reservas.routes.ReservaService")
    def test_get_active_reservation(self, mock_service, client):
        """Obtener reserva activa de un espacio."""
        reservation_id = str(uuid.uuid4())
        mock_reserva = MagicMock()
        mock_reserva.to_dict.return_value = {"id": reservation_id, "estado": "PENDING"}
        mock_service.get_active_reservation_by_space.return_value = mock_reserva

        response = client.get(f"/api/reservas/space/{uuid.uuid4()}/active")

        assert response.status_code == 200
        data = response.get_json()
        assert data["reservation"] is not None
        assert data["reservation"]["id"] == reservation_id

    @patch("reservas.routes.ReservaService")
    def test_get_active_reservation_none(self, mock_service, client):
        """Null si no hay reserva activa."""
        mock_service.get_active_reservation_by_space.return_value = None

        response = client.get(f"/api/reservas/space/{uuid.uuid4()}/active")

        assert response.status_code == 200
        data = response.get_json()
        assert data["reservation"] is None


class TestAdminEndpoints:
    """Tests para endpoints de admin."""

    @patch("reservas.routes.ReservaService")
    def test_get_pending_reservations_admin(self, mock_service, client, admin_auth_headers):
        """Admin puede ver reservas pendientes."""
        mock_reserva = MagicMock()
        mock_reserva.to_dict.return_value = {"id": str(uuid.uuid4()), "estado": "PENDING"}
        mock_service.get_pending_reservations.return_value = [mock_reserva]

        response = client.get(
            "/api/reservas/pending",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["reservations"]) == 1

    def test_get_pending_reservations_non_admin(self, client, auth_headers):
        """Usuario normal no puede ver reservas pendientes."""
        response = client.get(
            "/api/reservas/pending",
            headers=auth_headers,
        )

        assert response.status_code == 403

    def test_get_pending_reservations_unauthenticated(self, client):
        """Usuario no autenticado no puede ver reservas pendientes."""
        response = client.get("/api/reservas/pending")

        assert response.status_code == 401

    @patch("user_profiles.models.user_profile.UserProfile")
    @patch("spaces.models.space.Space")
    @patch("reservas.routes.ReservaService")
    def test_confirm_reservation_admin(self, mock_service, mock_space, mock_user_profile, client, admin_auth_headers):
        """Admin puede confirmar reserva."""
        reservation_id = str(uuid.uuid4())
        space_id = str(uuid.uuid4())

        # Mock de la reserva
        mock_reserva = MagicMock()
        mock_reserva.to_dict.return_value = {
            "id": reservation_id,
            "estado": "RESERVED",
        }
        mock_reserva.espacio_id = space_id
        mock_reserva.user_id = str(uuid.uuid4())
        mock_reserva.asignee = "Test Asignee"
        mock_service.confirm_reservation.return_value = (mock_reserva, None)

        # Mock del espacio
        mock_space_obj = MagicMock()
        mock_space_obj.plano_id = uuid.uuid4()
        mock_space.query.get.return_value = mock_space_obj

        # Mock del perfil de usuario
        mock_profile = MagicMock()
        mock_profile.company = "Test Company"
        mock_user_profile.query.filter_by.return_value.first.return_value = mock_profile

        response = client.post(
            f"/api/reservas/{reservation_id}/confirm",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["reservation"]["estado"] == "RESERVED"

    def test_confirm_reservation_non_admin(self, client, auth_headers):
        """Usuario normal no puede confirmar reserva."""
        response = client.post(
            f"/api/reservas/{uuid.uuid4()}/confirm",
            headers=auth_headers,
        )

        assert response.status_code == 403

    @patch("reservas.routes.ReservaService")
    def test_reject_reservation_admin(self, mock_service, client, admin_auth_headers):
        """Admin puede rechazar reserva."""
        mock_reserva = MagicMock()
        mock_reserva.to_dict.return_value = {
            "id": str(uuid.uuid4()),
            "estado": "CANCELLED",
        }
        mock_service.reject_reservation.return_value = (mock_reserva, None)

        response = client.post(
            f"/api/reservas/{uuid.uuid4()}/reject",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["reservation"]["estado"] == "CANCELLED"

    def test_reject_reservation_non_admin(self, client, auth_headers):
        """Usuario normal no puede rechazar reserva."""
        response = client.post(
            f"/api/reservas/{uuid.uuid4()}/reject",
            headers=auth_headers,
        )

        assert response.status_code == 403

    @patch("reservas.routes.ReservaService")
    def test_confirm_non_existing_reservation(self, mock_service, client, admin_auth_headers):
        """Error 404 al confirmar reserva inexistente."""
        mock_service.confirm_reservation.return_value = (None, "Reserva no encontrada")

        response = client.post(
            f"/api/reservas/{uuid.uuid4()}/confirm",
            headers=admin_auth_headers,
        )

        assert response.status_code == 404
