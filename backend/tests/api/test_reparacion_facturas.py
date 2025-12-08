# backend/tests/api/test_reparacion_facturas.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.equipo import Equipo
from app.models.incidencia import Incidencia
from app.models.reparacion import Reparacion
from app.core.file_manager import FileManager
from tests.utils import (
    create_user,
    create_random_equipo,
    get_auth_headers,
)

# --- FIXTURE DE LIMPIEZA ---
@pytest.fixture(autouse=True)
def clean_files(tmp_path):
    """
    Redirige el almacenamiento de archivos a una carpeta temporal
    durante los tests para no ensuciar el disco real.
    Se ejecuta automáticamente antes de cada test.
    """
    original_base = FileManager.BASE_DIR
    FileManager.BASE_DIR = tmp_path
    yield
    FileManager.BASE_DIR = original_base


# --- HELPER ---
def _crear_reparacion_via_api(client: TestClient, session: Session):
    """Crea equipo, incidencia y reparación vía API y devuelve (headers, rep_id)."""
    mant = create_user(session, role="MANTENIMIENTO")
    eq = create_random_equipo(session)
    headers = get_auth_headers(client, mant.username)

    # Crear incidencia
    resp_inc = client.post(
        "/api/v1/incidencias",
        json={
            "equipo_id": eq.id,
            "titulo": "Cambio de display",
            "descripcion": "La pantalla no enciende",
        },
        headers=headers,
    )
    assert resp_inc.status_code == 201, resp_inc.text
    inc_id = resp_inc.json()["id"]

    # Crear reparación
    resp_rep = client.post(
        "/api/v1/reparaciones",
        json={
            "equipo_id": eq.id,
            "incidencia_id": inc_id,
            "titulo": "Cambio de display",
            "estado": "EN_PROGRESO",
            "coste_materiales": 100.0,
            "coste_mano_obra": 50.0,
            "moneda": "EUR",
        },
        headers=headers,
    )
    assert resp_rep.status_code == 201, resp_rep.text
    rep_id = resp_rep.json()["id"]

    return headers, rep_id


# --- TESTS ---

def test_subir_y_listar_facturas_reparacion(client, session):
    """
    Subir una factura a una reparación y comprobar:
    - Se actualiza la reparación con los campos factura_*.
    - El listado /facturas devuelve 1 elemento correcto.
    """
    headers, rep_id = _crear_reparacion_via_api(client, session)

    files = {
        "file": ("factura1.pdf", b"PDF-DATA-1", "application/pdf"),
    }
    # CORRECCIÓN: Ruta en plural
    resp = client.post(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        files=files,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    rep = resp.json()
    assert rep["factura_archivo_nombre"] == "factura1.pdf"
    assert rep["factura_archivo_path"] is not None
    assert rep["factura_tamano_bytes"] is not None

    # Listar facturas
    resp_list = client.get(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        headers=headers,
    )
    assert resp_list.status_code == 200, resp_list.text
    data = resp_list.json()
    assert len(data) == 1
    assert data[0]["nombre_archivo"] == "factura1.pdf"
    assert data[0]["es_principal"] is True


def test_subir_segunda_factura_actualiza_principal(client, session):
    """
    Al subir una segunda factura:
    - Debe marcarse como principal.
    - La anterior pasa a es_principal=False.
    """
    headers, rep_id = _crear_reparacion_via_api(client, session)

    # Primera factura
    # CORRECCIÓN: Ruta en plural
    resp1 = client.post(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        files={"file": ("f1.pdf", b"PDF1", "application/pdf")},
        headers=headers,
    )
    assert resp1.status_code == 200
    # Segunda factura
    # CORRECCIÓN: Ruta en plural
    resp2 = client.post(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        files={"file": ("f2.pdf", b"PDF2", "application/pdf")},
        headers=headers,
    )
    assert resp2.status_code == 200

    # Listar facturas
    resp_list = client.get(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        headers=headers,
    )
    assert resp_list.status_code == 200
    facturas = resp_list.json()
    assert len(facturas) == 2

    # Solo una principal y debe ser la segunda
    principales = [f for f in facturas if f["es_principal"]]
    assert len(principales) == 1
    assert principales[0]["nombre_archivo"] == "f2.pdf"

    # Reparación debe apuntar a la segunda
    resp_rep = client.get(
        f"/api/v1/reparaciones/{rep_id}",
        headers=headers,
    )
    assert resp_rep.status_code == 200
    rep = resp_rep.json()
    assert rep["factura_archivo_nombre"] == "f2.pdf"


def test_descargar_factura_principal(client, session):
    """
    GET /reparaciones/{id}/factura devuelve la factura principal.
    """
    headers, rep_id = _crear_reparacion_via_api(client, session)

    # CORRECCIÓN: Ruta en plural para subir
    client.post(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        files={"file": ("factura_main.pdf", b"PDF-MAIN", "application/pdf")},
        headers=headers,
    )

    # La descarga de la principal sigue siendo en SINGULAR según routes_reparaciones.py
    # (revisa routes_reparaciones.py -> @router.get("/{reparacion_id}/factura")
    resp = client.get(
        f"/api/v1/reparaciones/{rep_id}/factura",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/pdf")
    # No comprobamos el cuerpo entero, solo que no viene vacío
    assert resp.content  # hay datos


def test_eliminar_factura_reasigna_principal_o_limpia(client, session):
    """
    Eliminar una factura:
    - Si era la principal y queda otra, esa otra pasa a principal.
    - Si era la única, la reparación queda sin factura_*.
    """
    headers, rep_id = _crear_reparacion_via_api(client, session)

    # Subir dos facturas
    # CORRECCIÓN: Ruta en plural
    client.post(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        files={"file": ("f1.pdf", b"PDF1", "application/pdf")},
        headers=headers,
    )
    client.post(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        files={"file": ("f2.pdf", b"PDF2", "application/pdf")},
        headers=headers,
    )

    # Listar y localizar la principal (debe ser f2)
    resp_list = client.get(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        headers=headers,
    )
    facturas = resp_list.json()
    principal = [f for f in facturas if f["es_principal"]][0]
    secundaria = [f for f in facturas if not f["es_principal"]][0]

    # Borrar la principal
    # CORRECCIÓN: Ruta en plural /facturas/{id}
    resp_del = client.delete(
        f"/api/v1/reparaciones/{rep_id}/facturas/{principal['id']}",
        headers=headers,
    )
    assert resp_del.status_code == 204

    # La otra debe seguir existiendo y ser principal
    resp_list2 = client.get(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        headers=headers,
    )
    facturas2 = resp_list2.json()
    assert len(facturas2) == 1
    assert facturas2[0]["id"] == secundaria["id"]
    assert facturas2[0]["es_principal"] is True

    # Ahora borramos la última
    # CORRECCIÓN: Ruta en plural
    resp_del2 = client.delete(
        f"/api/v1/reparaciones/{rep_id}/facturas/{secundaria['id']}",
        headers=headers,
    )
    assert resp_del2.status_code == 204

    # Reparación sin factura principal
    resp_rep = client.get(
        f"/api/v1/reparaciones/{rep_id}",
        headers=headers,
    )
    rep = resp_rep.json()
    assert rep["factura_archivo_nombre"] is None
    assert rep["factura_archivo_path"] is None


def test_subir_factura_requiere_permiso_mantenimiento_o_admin(client, session):
    """
    Un usuario OPERARIO no debería poder subir facturas.
    """
    # Crear reparación como MANTENIMIENTO
    mant = create_user(session, role="MANTENIMIENTO")
    eq = create_random_equipo(session)
    mant_headers = get_auth_headers(client, mant.username)

    # incidencia + reparación
    resp_inc = client.post(
        "/api/v1/incidencias",
        json={
            "equipo_id": eq.id,
            "titulo": "Test permisos",
            "descripcion": "Desc",
        },
        headers=mant_headers,
    )
    inc_id = resp_inc.json()["id"]
    resp_rep = client.post(
        "/api/v1/reparaciones",
        json={
            "equipo_id": eq.id,
            "incidencia_id": inc_id,
            "titulo": "Rep permisos",
        },
        headers=mant_headers,
    )
    rep_id = resp_rep.json()["id"]

    # Usuario OPERARIO
    op = create_user(session, role="OPERARIO")
    op_headers = get_auth_headers(client, op.username)

    # CORRECCIÓN: Ruta en plural
    resp = client.post(
        f"/api/v1/reparaciones/{rep_id}/facturas",
        files={"file": ("forbidden.pdf", b"XXX", "application/pdf")},
        headers=op_headers,
    )
    assert resp.status_code in (401, 403)