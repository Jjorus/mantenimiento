# backend/tests/api/test_ubicaciones.py
import pytest
from sqlmodel import select
from app.models.ubicacion import Ubicacion
from app.models.usuario import Usuario
from tests.utils import create_user, get_auth_headers

# -------------------------------------------------------------------------
# 1. CREACIÓN DE UBICACIONES (Happy Paths)
# -------------------------------------------------------------------------

def test_crear_ubicacion_estandar(client, session):
    """
    Un ADMIN crea una ubicación física normal (ALMACEN).
    """
    admin = create_user(session, role="ADMIN")
    headers = get_auth_headers(client, admin.username)

    payload = {
        "nombre": "Almacén Norte",
        "tipo": "ALMACEN",
    }

    response = client.post("/api/v1/ubicaciones", json=payload, headers=headers)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["nombre"] == "Almacén Norte"
    assert data["tipo"] == "ALMACEN"
    # En una ubicación estándar no debe haber usuario asociado
    assert data.get("usuario_id") is None


def test_crear_ubicacion_tecnico(client, session):
    """
    Un ADMIN crea una ubicación lógica para un TÉCNICO.
    """
    admin = create_user(session, role="ADMIN")
    tecnico = create_user(session, role="OPERARIO")

    headers = get_auth_headers(client, admin.username)

    payload = {
        "nombre": f"Mochila de {tecnico.username}",
        "tipo": "TECNICO",
        "usuario_id": tecnico.id,
    }

    response = client.post("/api/v1/ubicaciones", json=payload, headers=headers)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["tipo"] == "TECNICO"
    assert data["usuario_id"] == tecnico.id

# -------------------------------------------------------------------------
# 2. VALIDACIONES DE NEGOCIO (Sad Paths)
# -------------------------------------------------------------------------

def test_error_asignar_usuario_a_almacen(client, session):
    """
    No se permite asignar usuario_id si el tipo no es TECNICO.
    Debe devolver 422.
    """
    admin = create_user(session, role="ADMIN")
    tecnico = create_user(session, role="OPERARIO")
    headers = get_auth_headers(client, admin.username)

    payload = {
        "nombre": "Almacén Error",
        "tipo": "ALMACEN",      # Tipo incompatible con usuario
        "usuario_id": tecnico.id,
    }

    response = client.post("/api/v1/ubicaciones", json=payload, headers=headers)

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert isinstance(detail, list) and len(detail) > 0
    msg = detail[0]["msg"]
    # No forzamos el texto exacto, pero sí que mencione TÉCNICO
    assert "TECNICO" in msg


def test_error_usuario_inexistente(client, session):
    """
    Intentar asignar un usuario que no existe.
    """
    admin = create_user(session, role="ADMIN")
    headers = get_auth_headers(client, admin.username)

    payload = {
        "nombre": "Ubi Fantasma",
        "tipo": "TECNICO",
        "usuario_id": 999999,  # ID inexistente
    }

    response = client.post("/api/v1/ubicaciones", json=payload, headers=headers)

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert isinstance(detail, list) and len(detail) > 0
    assert "inexistente" in detail[0]["msg"].lower()

# -------------------------------------------------------------------------
# 3. RESTRICCIONES DE INTEGRIDAD (Unicidad 1-to-1)
# -------------------------------------------------------------------------

def test_unicidad_tecnico_ubicacion(client, session):
    """
    Un técnico NO puede tener dos ubicaciones personales.
    La segunda creación debe fallar (409 Conflict).
    """
    admin = create_user(session, role="ADMIN")
    tecnico = create_user(session, role="OPERARIO")
    headers = get_auth_headers(client, admin.username)

    # 1. Crear la primera ubicación para el técnico
    first_resp = client.post(
        "/api/v1/ubicaciones",
        json={
            "nombre": "Ubi 1",
            "tipo": "TECNICO",
            "usuario_id": tecnico.id,
        },
        headers=headers,
    )
    assert first_resp.status_code == 201, first_resp.text

    # 2. Intentar crear la segunda para el MISMO técnico
    response = client.post(
        "/api/v1/ubicaciones",
        json={
            "nombre": "Ubi 2 (Duplicada)",
            "tipo": "TECNICO",
            "usuario_id": tecnico.id,  # Conflicto unique
        },
        headers=headers,
    )

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert "conflicto" in detail.lower() or "integr" in detail.lower()

# -------------------------------------------------------------------------
# 4. EDICIÓN Y CICLO DE VIDA
# -------------------------------------------------------------------------

def test_convertir_almacen_en_tecnico(client, session):
    """
    Cambiamos una ubicación existente:
    De tipo OTRO (sin usuario) -> tipo TECNICO (con usuario).
    """
    admin = create_user(session, role="ADMIN")
    tecnico = create_user(session, role="OPERARIO")
    headers = get_auth_headers(client, admin.username)

    # 1. Crear ubicación genérica
    create_resp = client.post(
        "/api/v1/ubicaciones",
        json={
            "nombre": "Caja Herramientas",
            "tipo": "OTRO",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    ubi_id = create_resp.json()["id"]

    # 2. Actualizarla (PATCH) para asignarla al técnico
    patch_resp = client.patch(
        f"/api/v1/ubicaciones/{ubi_id}",
        json={
            "tipo": "TECNICO",
            "usuario_id": tecnico.id,
        },
        headers=headers,
    )

    assert patch_resp.status_code == 200, patch_resp.text
    data = patch_resp.json()
    assert data["tipo"] == "TECNICO"
    assert data["usuario_id"] == tecnico.id
