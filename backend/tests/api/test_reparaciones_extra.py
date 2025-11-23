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
    # Usamos el helper para obtener headers de un usuario con rol válido
    headers, _ = _crear_reparacion_via_api(client, session)

    payload = {
        "equipo_id": 999_999,        # ID muy alto para asegurar que no existe
        "incidencia_id": 999_998,    # Tampoco importa si existe o no
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
    # Creamos contexto con datos válidos (equipo/incidencia reales en BD)
    headers, _ = _crear_reparacion_via_api(client, session)

    # Tomamos un equipo real de la BD
    equipo = session.exec(select(Equipo)).first()
    assert equipo is not None, "Debe existir al menos un equipo en BD para este test"

    payload = {
        "equipo_id": equipo.id,
        "incidencia_id": 999_999,  # incidencia que no existe
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
    # Creamos primero una reparación válida para tener incidencia real
    headers, rep_id = _crear_reparacion_via_api(client, session)

    rep = session.get(Reparacion, rep_id)
    assert rep is not None
    assert rep.incidencia_id is not None

    # Forzamos un equipo distinto al de la incidencia
    # (aunque ese equipo no exista, la lógica compara solo IDs)
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
    Subir una factura con un MIME no permitido (por ejemplo text/plain)
    -> 422 y mensaje de tipo no permitido.
    """
    headers, rep_id = _crear_reparacion_via_api(client, session)

    resp = client.post(
        f"/api/v1/reparaciones/{rep_id}/factura",
        files={"file": ("nota.txt", b"contenido", "text/plain")},
        headers=headers,
    )

    assert resp.status_code == 422
    data = resp.json()
    assert "Tipo de archivo no permitido" in data["detail"]


def test_descargar_factura_sin_factura_da_404(client, session):
    """
    Intentar descargar la factura principal de una reparación que no tiene facturas
    -> 404 (mensaje genérico o específico según handler global).
    """
    headers, rep_id = _crear_reparacion_via_api(client, session)

    resp = client.get(f"/api/v1/reparaciones/{rep_id}/factura", headers=headers)
    assert resp.status_code == 404
    data = resp.json()

    # Aceptamos tanto el mensaje específico del endpoint como el genérico del handler global
    assert (
    "factura" in data["detail"].lower()
    or "no encontrado" in data["detail"].lower()
)


# ============================================================
# SEGURIDAD - Accesos no autorizados y ataques básicos
# ============================================================

def test_listar_reparaciones_sin_token_rechazado(client):
    """
    Asegura que un endpoint protegido no se puede usar sin autenticación.
    """
    resp = client.get("/api/v1/reparaciones")
    # Dependiendo de tu config, puede ser 401 (lo normal) o 403.
    assert resp.status_code in (401, 403)


def test_listar_reparaciones_con_token_invalido_rechazado(client):
    """
    Asegura que un JWT inventado no permite acceder a endpoints protegidos.
    """
    headers = {"Authorization": "Bearer invalid.token.value"}
    resp = client.get("/api/v1/reparaciones", headers=headers)
    assert resp.status_code in (401, 403)


def test_sql_injection_en_login_no_funciona(client):
    """
    Intento de SQL injection básico en login:
    username = "' OR 1=1--"
    -> debe devolver error (4xx), nunca 200.
    """
    resp = client.post(
        "/api/auth/login",
        data={"username": "' OR 1=1--", "password": "loquesea"},
    )

    # Cualquier código 4xx es válido aquí, pero NO debe ser 200.
    assert 400 <= resp.status_code < 500
