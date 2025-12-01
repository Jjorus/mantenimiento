# backend/tests/api/test_reparaciones_estados.py
import pytest
from sqlmodel import Session

from app.models.equipo import Equipo
from app.models.incidencia import Incidencia
from tests.utils import create_user, create_random_equipo, get_auth_headers


def test_crear_reparacion_actualiza_estado_equipo_e_incidencia(client, session: Session):
    """
    Al crear una reparación asociada a una incidencia:
    - El equipo debe pasar a estado MANTENIMIENTO.
    - La incidencia debe pasar de ABIERTA a EN_PROGRESO.
    """
    mant = create_user(session, role="MANTENIMIENTO")
    headers = get_auth_headers(client, mant.username)

    # Equipo inicialmente OPERATIVO
    eq = create_random_equipo(session)
    session.refresh(eq)
    assert eq.estado == "OPERATIVO"

    # Crear incidencia (estado por defecto = ABIERTA)
    resp_inc = client.post(
        "/api/v1/incidencias",
        json={
            "equipo_id": eq.id,
            "titulo": "Fallo en equipo",
            "descripcion": "No mide correctamente",
        },
        headers=headers,
    )
    assert resp_inc.status_code == 201, resp_inc.text
    inc_data = resp_inc.json()
    inc_id = inc_data["id"]
    assert inc_data["estado"] == "ABIERTA"

    # Crear reparación asociada
    resp_rep = client.post(
        "/api/v1/reparaciones",
        json={
            "equipo_id": eq.id,
            "incidencia_id": inc_id,
            "titulo": "Reparación de fallo",
            "descripcion": "Se revisa el equipo en taller",
            # estado no obligatorio, por defecto ABIERTA
        },
        headers=headers,
    )
    assert resp_rep.status_code == 201, resp_rep.text

    # Refrescar desde BD
    session.refresh(eq)
    inc = session.get(Incidencia, inc_id)

    assert eq.estado == "MANTENIMIENTO"
    assert inc.estado == "EN_PROGRESO"
