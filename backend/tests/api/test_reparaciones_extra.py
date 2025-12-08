# backend/tests/api/test_reparaciones_extra.py
import pytest
from sqlmodel import select

from app.models.equipo import Equipo
from app.models.reparacion import Reparacion
from tests.api.test_reparacion_facturas import _crear_reparacion_via_api


# ============================================================
# BLOQUE A - Validaciones de creación de reparación
# ============================================================

def test_crear_reparacion_equipo_inexistente(client, session):
    """
    Crear una reparación con un equipo que no existe
    -> 422 y mensaje 'Equipo inexistente'.
    """
    headers, _ = _crear_reparacion_via_api(client, session)

    payload = {
        "equipo_id": 999_999,
        "incidencia_id": 999_998,
        "titulo": "Reparación con equipo inexistente",
        "descripcion": "Test equipo inexistente",
        "estado": "ABIERTA",
        "coste_materiales": 0,
        "coste_mano_obra": 0,
        "coste_otros": 0,
        "moneda": "EUR",
        "proveedor": None,
        "numero_factura": None,
    }

    resp = client.post("/api/v1/reparaciones", json=payload, headers=headers)
    assert resp.status_code == 422

    data = resp.json()
    assert isinstance(data["detail"], list)
    msgs = [err["msg"] for err in data["detail"]]
    assert "Equipo inexistente" in msgs


def test_crear_reparacion_incidencia_inexistente(client, session):
    """
    Crear una reparación con una incidencia que no existe
    -> 422 y mensaje 'Incidencia inexistente'.
    """
    headers, _ = _crear_reparacion_via_api(client, session)

    equipo = session.exec(select(Equipo)).first()
    assert equipo is not None, "Debe existir al menos un equipo en BD para este test"

    payload = {
        "equipo_id": equipo.id,
        "incidencia_id": 999_999,
        "titulo": "Reparación con incidencia inexistente",
        "descripcion": "Test incidencia inexistente",
        "estado": "ABIERTA",
        "coste_materiales": 0,
        "coste_mano_obra": 0,
        "coste_otros": 0,
        "moneda": "EUR",
        "proveedor": None,
        "numero_factura": None,
    }

    resp = client.post("/api/v1/reparaciones", json=payload, headers=headers)
    assert resp.status_code == 422

    data = resp.json()
    msgs = [err["msg"] for err in data["detail"]]
    assert "Incidencia inexistente" in msgs


def test_crear_reparacion_incidencia_no_pertenece_a_equipo(client, session):
    """
    Crear una reparación donde la incidencia no pertenece al equipo indicado:
    -> 422 y mensaje 'La incidencia no pertenece a ese equipo'.
    """
    headers, rep_id = _crear_reparacion_via_api(client, session)

    rep = session.get(Reparacion, rep_id)
    assert rep is not None
    assert rep.incidencia_id is not None

    equipo_erroneo_id = rep.equipo_id + 999

    payload = {
        "equipo_id": equipo_erroneo_id,
        "incidencia_id": rep.incidencia_id,
        "titulo": "Reparación con incidencia de otro equipo",
        "descripcion": "Test incidencia no pertenece al equipo",
        "estado": "ABIERTA",
        "coste_materiales": 0,
        "coste_mano_obra": 0,
        "coste_otros": 0,
        "moneda": "EUR",
        "proveedor": None,
        "numero_factura": None,
    }

    resp = client.post("/api/v1/reparaciones", json=payload, headers=headers)
    assert resp.status_code == 422

    data = resp.json()
    msgs = [err["msg"] for err in data["detail"]]
    assert "La incidencia no pertenece a ese equipo" in msgs


# ============================================================
# BLOQUE B - Errores de facturas
# ============================================================

def test_subir_factura_mime_no_permitido(client, session):
    """
    Subir un archivo peligroso (ej. .exe) debe ser rechazado.
    -> 422 y mensaje de tipo no permitido.
    """
    headers, rep_id = _crear_reparacion_via_api(client, session)

    # CAMBIO: Usamos 'application/x-msdownload' (ejecutable) que NO está en permitidos
    resp = client.post(
        f"/api/v1/reparaciones/{rep_id}/factura",
        files={"file": ("virus.exe", b"MZ...", "application/x-msdownload")},
        headers=headers,
    )

    assert resp.status_code == 422
    data = resp.json()
    assert "Tipo de archivo no permitido" in data["detail"]


def test_descargar_factura_sin_factura_da_404(client, session):
    """
    Intentar descargar la factura principal de una reparación que no tiene facturas
    -> 404.
    """
    headers, rep_id = _crear_reparacion_via_api(client, session)

    resp = client.get(f"/api/v1/reparaciones/{rep_id}/factura", headers=headers)
    assert resp.status_code == 404
    data = resp.json()

    assert (
        "factura" in data["detail"].lower()
        or "no encontrado" in data["detail"].lower()
    )


# ============================================================
# SEGURIDAD
# ============================================================

def test_listar_reparaciones_sin_token_rechazado(client):
    resp = client.get("/api/v1/reparaciones")
    assert resp.status_code in (401, 403)


def test_listar_reparaciones_con_token_invalido_rechazado(client):
    headers = {"Authorization": "Bearer invalid.token.value"}
    resp = client.get("/api/v1/reparaciones", headers=headers)
    assert resp.status_code in (401, 403)


def test_sql_injection_en_login_no_funciona(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "' OR 1=1--", "password": "loquesea"},
    )
    assert 400 <= resp.status_code < 500