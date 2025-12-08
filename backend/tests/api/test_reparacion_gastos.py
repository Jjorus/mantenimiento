# backend/tests/api/test_reparacion_gastos.py
import pytest
from sqlmodel import Session
from app.models.reparacion import Reparacion
from app.models.reparacion_gasto import ReparacionGasto
from tests.utils import create_user, create_random_equipo, get_auth_headers

@pytest.fixture(name="setup_reparacion")
def fixture_setup_reparacion(client, session: Session):
    """
    Fixture que prepara el escenario base:
    1. Crea un usuario MANTENIMIENTO.
    2. Crea un Equipo y una Incidencia.
    3. Crea una Reparación vacía.
    Retorna: (headers, reparacion_id)
    """
    # 1. Usuario con permisos
    user = create_user(session, role="MANTENIMIENTO")
    headers = get_auth_headers(client, user.username)

    # 2. Equipo
    equipo = create_random_equipo(session)
    
    # 3. Incidencia
    # CORRECCIÓN: Título y descripción más largos para pasar validación (min=3)
    resp_inc = client.post(
        "/api/v1/incidencias",
        json={
            "equipo_id": equipo.id, 
            "titulo": "Incidencia Test", 
            "descripcion": "Descripción válida"
        },
        headers=headers
    )
    assert resp_inc.status_code == 201, resp_inc.text
    inc_id = resp_inc.json()["id"]

    # 4. Reparación
    # CORRECCIÓN: Título más largo
    resp_rep = client.post(
        "/api/v1/reparaciones",
        json={
            "equipo_id": equipo.id,
            "incidencia_id": inc_id,
            "titulo": "Reparación Test",
            "descripcion": "Testing costes"
        },
        headers=headers
    )
    assert resp_rep.status_code == 201, resp_rep.text
    rep_id = resp_rep.json()["id"]
    
    return headers, rep_id

def test_flujo_gastos_recalculo_automatico(client, session: Session, setup_reparacion):
    """
    Prueba que al añadir gastos de diferentes tipos, la Reparación
    actualiza automáticamente sus columnas de costes.
    """
    headers, rep_id = setup_reparacion

    # --- 1. Añadir Gasto de MATERIALES ---
    gasto_mat = {
        "descripcion": "Motor Nuevo",
        "importe": 100.50,
        "tipo": "MATERIALES"
    }
    resp = client.post(f"/api/v1/reparaciones/{rep_id}/gastos", json=gasto_mat, headers=headers)
    assert resp.status_code == 200
    
    # Verificar respuesta (debe devolver la REPARACIÓN actualizada)
    data = resp.json()
    # Usamos float() para asegurar compatibilidad si viene como string/decimal
    assert float(data["coste_materiales"]) == 100.50
    assert float(data["coste_mano_obra"]) == 0.0
    assert float(data["coste_otros"]) == 0.0

    # --- 2. Añadir Gasto de MANO_OBRA ---
    gasto_mo = {
        "descripcion": "3 Horas Técnico",
        "importe": 90.00,
        "tipo": "MANO_OBRA"
    }
    resp = client.post(f"/api/v1/reparaciones/{rep_id}/gastos", json=gasto_mo, headers=headers)
    assert resp.status_code == 200
    
    # Verificar que se suman independientemente
    data = resp.json()
    assert float(data["coste_materiales"]) == 100.50
    assert float(data["coste_mano_obra"]) == 90.00

    # --- 3. Añadir otro gasto de MATERIALES (debe sumar al anterior) ---
    gasto_mat_2 = {
        "descripcion": "Aceite",
        "importe": 20.00,
        "tipo": "MATERIALES"
    }
    resp = client.post(f"/api/v1/reparaciones/{rep_id}/gastos", json=gasto_mat_2, headers=headers)
    assert resp.status_code == 200
    
    data = resp.json()
    # 100.50 + 20.00 = 120.50
    assert float(data["coste_materiales"]) == 120.50 
    assert float(data["coste_mano_obra"]) == 90.00

    # Verificar persistencia en BD
    session.expire_all()
    rep_db = session.get(Reparacion, rep_id)
    assert float(rep_db.coste_materiales) == 120.50
    assert float(rep_db.coste_mano_obra) == 90.00
    
    # Validar coste_total (computed field) si es posible, o suma manual
    coste_total = (rep_db.coste_materiales or 0) + (rep_db.coste_mano_obra or 0) + (rep_db.coste_otros or 0)
    assert float(coste_total) == 210.50

def test_listar_y_eliminar_gastos(client, session: Session, setup_reparacion):
    """
    Prueba listar los gastos añadidos y borrar uno para ver si resta el importe.
    """
    headers, rep_id = setup_reparacion

    # Crear dos gastos
    client.post(f"/api/v1/reparaciones/{rep_id}/gastos", json={"descripcion": "G1", "importe": 50, "tipo": "OTROS"}, headers=headers)
    client.post(f"/api/v1/reparaciones/{rep_id}/gastos", json={"descripcion": "G2", "importe": 20, "tipo": "OTROS"}, headers=headers)

    # --- 1. Listar Gastos ---
    resp_list = client.get(f"/api/v1/reparaciones/{rep_id}/gastos", headers=headers)
    assert resp_list.status_code == 200
    gastos = resp_list.json()
    assert len(gastos) == 2
    
    # Obtenemos el ID del primer gasto para borrarlo
    gasto_id_a_borrar = gastos[0]["id"]
    importe_a_restar = gastos[0]["importe"]

    # Verificar estado actual de la reparación
    session.expire_all()
    rep_antes = session.get(Reparacion, rep_id)
    assert float(rep_antes.coste_otros) == 70.0 # 50 + 20

    # --- 2. Eliminar Gasto ---
    resp_del = client.delete(f"/api/v1/reparaciones/{rep_id}/gastos/{gasto_id_a_borrar}", headers=headers)
    assert resp_del.status_code == 200
    
    # La respuesta del delete es la Reparación actualizada
    data_del = resp_del.json()
    # 70 - 50 = 20
    assert float(data_del["coste_otros"]) == 20.0

    # Verificar que el gasto ya no existe en la lista
    resp_list_2 = client.get(f"/api/v1/reparaciones/{rep_id}/gastos", headers=headers)
    assert len(resp_list_2.json()) == 1