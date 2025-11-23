# tests/api/test_mantenimiento.py

import pytest
from tests.utils import create_user, get_auth_headers, create_random_equipo


def test_ciclo_vida_incidencia(client, session):
    """
    Ciclo completo de una incidencia:
    - Operario crea incidencia.
    - Mantenimiento la cierra.
    - Se verifica que el cierre y la auditoría son correctos.
    """
    op = create_user(session, role="OPERARIO")
    mant = create_user(session, role="MANTENIMIENTO")
    eq = create_random_equipo(session)

    # 1. Operario crea incidencia
    headers_op = get_auth_headers(client, op.username)
    resp = client.post(
        "/api/v1/incidencias",
        json={
            "equipo_id": eq.id,
            "titulo": "Pantalla rota",
            "descripcion": "Se cayó al suelo",
        },
        headers=headers_op,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    inc_id = data["id"]
    assert data["estado"] == "ABIERTA"

    # 2. Mantenimiento la cierra
    headers_mant = get_auth_headers(client, mant.username)
    resp = client.post(f"/api/v1/incidencias/{inc_id}/cerrar", headers=headers_mant)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["estado"] == "CERRADA"
    # Auditoría
    assert data["cerrada_por_id"] == mant.id
    assert data["cerrada_en"] is not None


def test_reparacion_flujo_basico(client, session):
    """
    Gestión de reparaciones (Solo Mantenimiento/Admin).
    - Crea incidencia.
    - Crea reparación asociada.
    - Cierra reparación.
    """
    mant = create_user(session, role="MANTENIMIENTO")
    eq = create_random_equipo(session)
    headers = get_auth_headers(client, mant.username)

    # 0. Crear incidencia para ese equipo (requisito de dominio)
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

    # 1. Crear Reparación asociada a la incidencia
    resp = client.post(
        "/api/v1/reparaciones",
        json={
            "equipo_id": eq.id,
            "incidencia_id": inc_id,
            "titulo": "Cambio de display",
            "estado": "EN_PROGRESO",
            # Opcionales: costes iniciales
            "coste_materiales": 100.0,
            "coste_mano_obra": 50.0,
            "moneda": "EUR",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    rep = resp.json()
    rep_id = rep["id"]

    assert rep["estado"] == "EN_PROGRESO"

    # Numeric(10,2) se serializa como string ("100.00"), así que comparamos como float
    assert float(rep["coste_materiales"]) == 100.0
    assert float(rep["coste_mano_obra"]) == 50.0
    assert rep["moneda"] == "EUR"

    # 2. Cerrar Reparación
    resp = client.post(
        f"/api/v1/reparaciones/{rep_id}/cerrar",
        json={},  # fecha_fin opcional, usa now() si no se envía
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["estado"] == "CERRADA"
    # duracion_dias es un computed_field en el modelo
    assert data["duracion_dias"] is not None
