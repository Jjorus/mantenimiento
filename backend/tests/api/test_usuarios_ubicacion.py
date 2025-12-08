# backend/tests/api/test_usuarios_ubicacion.py
import pytest
from sqlmodel import Session

from app.models.ubicacion import Ubicacion
from tests.utils import create_user, get_auth_headers, random_string


def _crear_ubicacion_tecnico(session: Session) -> Ubicacion:
    ubi = Ubicacion(
        nombre=f"Tecnico-{random_string(4)}",
        tipo="TECNICO",
        seccion_id=None,
    )
    session.add(ubi)
    session.commit()
    session.refresh(ubi)
    return ubi


@pytest.mark.parametrize("role", ["OPERARIO", "MANTENIMIENTO"])
def test_admin_crea_usuario_con_ubicacion(client, session, role):
    admin = create_user(session, role="ADMIN")
    headers = get_auth_headers(client, admin.username)

    ubicacion = _crear_ubicacion_tecnico(session)

    username = f"u_{random_string(5)}"
    payload = {
        "username": username,
        "email": f"{username}@test.com",
        "password": "password123",
        "role": role,
        "active": True,
        "ubicacion_id": ubicacion.id,
    }

    resp = client.post("/api/v1/usuarios", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["username"] == username
    assert data["ubicacion_id"] == ubicacion.id

    session.refresh(ubicacion)
    assert ubicacion.usuario_id == data["id"]


def test_admin_actualiza_ubicacion_usuario(client, session):
    admin = create_user(session, role="ADMIN")
    headers = get_auth_headers(client, admin.username)

    # Usuario y dos ubicaciones de técnico
    user = create_user(session, role="OPERARIO")
    ubi1 = _crear_ubicacion_tecnico(session)
    ubi2 = _crear_ubicacion_tecnico(session)

    # Asignar primera ubicación
    resp1 = client.patch(
        f"/api/v1/usuarios/{user.id}",
        json={"ubicacion_id": ubi1.id},
        headers=headers,
    )
    assert resp1.status_code == 200, resp1.text
    data1 = resp1.json()
    assert data1["ubicacion_id"] == ubi1.id

    session.refresh(ubi1)
    assert ubi1.usuario_id == user.id

    # Cambiar a segunda ubicación
    resp2 = client.patch(
        f"/api/v1/usuarios/{user.id}",
        json={"ubicacion_id": ubi2.id},
        headers=headers,
    )
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert data2["ubicacion_id"] == ubi2.id

    session.refresh(ubi1)
    session.refresh(ubi2)
    assert ubi1.usuario_id is None
    assert ubi2.usuario_id == user.id
