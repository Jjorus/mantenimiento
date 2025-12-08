# tests/api/test_equipos.py
import pytest
from app.models.equipo import Equipo
from sqlmodel import select
from tests.utils import create_user, get_auth_headers, create_random_equipo


def test_crud_equipo_admin(client, session):
    """
    ADMIN puede crear, leer, actualizar y listar equipos.
    *Actualizado para verificar el campo 'notas'*
    """
    admin = create_user(session, role="ADMIN")
    headers = get_auth_headers(client, admin.username)

    # 1. Crear (incluyendo notas)
    payload = {
        "identidad": "EQ-ADMIN-01",
        "numero_serie": "SN-ADMIN-01",
        "tipo": "Analizador",
        "estado": "OPERATIVO",
        "notas": "Nota inicial de prueba para inventario"  # <--- NUEVO
    }
    resp = client.post("/api/v1/equipos", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    eq_id = data["id"]
    
    # Verificaciones
    assert data["identidad"] == "EQ-ADMIN-01" # Debe respetar la escritura original
    assert data["numero_serie"] == "SN-ADMIN-01"
    assert data["notas"] == "Nota inicial de prueba para inventario" # <--- Verificamos persistencia

    # 2. Leer individual
    resp = client.get(f"/api/v1/equipos/{eq_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["notas"] == "Nota inicial de prueba para inventario"

    # 3. Actualizar (PATCH) notas
    patch_payload = {
        "notas": "Nota editada y actualizada" # <--- Probamos la edición
    }
    resp = client.patch(f"/api/v1/equipos/{eq_id}", json=patch_payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["notas"] == "Nota editada y actualizada"

    # 4. Verificar persistencia tras actualización
    resp = client.get(f"/api/v1/equipos/{eq_id}", headers=headers)
    assert resp.json()["notas"] == "Nota editada y actualizada"

    # 5. Listar (búsqueda)
    resp = client.get("/api/v1/equipos?q=admin", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_unicidad_identidad_y_nfc(client, session):
    """
    No se pueden crear dos equipos con misma identidad o NFC.
    La API devuelve 422 con detalle por campo.
    """
    admin = create_user(session, role="ADMIN")
    headers = get_auth_headers(client, admin.username)

    # Equipo A
    resp_a = client.post(
        "/api/v1/equipos",
        json={
            "identidad": "EQ-UNIQUE",
            "tipo": "Otro",        # tipo válido según TIPOS_VALIDOS
            "nfc_tag": "tag_unico",
            "notas": "Nota equipo A"
        },
        headers=headers,
    )
    assert resp_a.status_code == 201, resp_a.text

    # Equipo B (Duplicando identidad, case-insensitive)
    resp = client.post(
        "/api/v1/equipos",
        json={
            "identidad": "eq-unique",  # choque case-insensitive
            "tipo": "Analizador",      # otro tipo válido
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert isinstance(body.get("detail"), list)
    assert any(
        "identidad" in err.get("loc", [])
        for err in body["detail"]
    )

    # Equipo C (Duplicando NFC, case-insensitive)
    resp = client.post(
        "/api/v1/equipos",
        json={
            "identidad": "EQ-OTRO",
            "tipo": "Analizador",
            "nfc_tag": "TAG_UNICO",  # mismo NFC, distinto caso
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert isinstance(body.get("detail"), list)
    assert any(
        "nfc_tag" in err.get("loc", [])
        for err in body["detail"]
    )


def test_buscar_equipo_por_nfc_endpoint(client, session):
    """
    Probar el endpoint específico de búsqueda por NFC (/buscar/nfc/{tag}).
    """
    user = create_user(session, role="OPERARIO")
    eq = create_random_equipo(session)
    eq.nfc_tag = "my_super_tag"
    session.add(eq)
    session.commit()

    headers = get_auth_headers(client, user.username)

    # Búsqueda insensible a mayúsculas
    resp = client.get("/api/v1/equipos/buscar/nfc/MY_SUPER_TAG", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == eq.id