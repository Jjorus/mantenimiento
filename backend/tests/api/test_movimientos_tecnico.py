# backend/tests/api/test_movimientos_tecnico.py
import pytest
from sqlmodel import select
from app.models.equipo import Equipo
from app.models.ubicacion import Ubicacion
from app.models.movimiento import Movimiento
from tests.utils import create_user, get_auth_headers, create_random_equipo

# -------------------------------------------------------------------------
# 1. NUEVA FUNCIONALIDAD: RETIRAR PARA MÍ (Técnico)
# -------------------------------------------------------------------------

def test_retirar_para_mi_exito(client, session):
    """
    Escenario: Técnico con ubicación personal retira equipo.
    Resultado: Equipo se mueve a su ubicación y se crea historial.
    """
    # 1. Preparar datos: Técnico y su ubicación personal
    tech = create_user(session, role="OPERARIO")
    ubi_tech = Ubicacion(
        nombre=f"Personal: {tech.username}",
        tipo="TECNICO",
        usuario_id=tech.id,
    )
    session.add(ubi_tech)
    session.commit()
    session.refresh(ubi_tech)

    # Equipo en almacén (estado por defecto OPERATIVO)
    eq = create_random_equipo(session, tipo="Multímetro")

    # 2. Ejecutar acción (Login + Request)
    headers = get_auth_headers(client, tech.username)
    payload = {"equipo_id": eq.id, "comentario": "Me lo llevo a obra"}

    resp = client.post("/api/v1/movimientos/retirar/me", json=payload, headers=headers)

    # 3. Validaciones
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["equipo_id"] == eq.id
    assert data["hacia_ubicacion_id"] == ubi_tech.id

    session.refresh(eq)
    assert eq.ubicacion_id == ubi_tech.id

    mov = session.get(Movimiento, data["id"])
    assert mov.comentario == "Me lo llevo a obra"
    assert mov.usuario_id == tech.id


def test_retirar_para_mi_error_sin_configuracion(client, session):
    """
    Escenario: Técnico intenta retirar, pero NO tiene ubicación asignada.
    Resultado: Error 422 (Protección robusta).
    """
    # Técnico SIN ubicación personal
    tech_novato = create_user(session, role="OPERARIO")
    eq = create_random_equipo(session)

    headers = get_auth_headers(client, tech_novato.username)

    resp = client.post(
        "/api/v1/movimientos/retirar/me",
        json={"equipo_id": eq.id},
        headers=headers,
    )

    assert resp.status_code == 422, resp.text

    detail = resp.json()["detail"]
    # detail es una lista de errores estilo FastAPI
    assert isinstance(detail, list)
    msg = detail[0]["msg"]
    # Verificamos que el mensaje ayuda a entender el problema
    assert "ubicación de técnico" in msg.lower()



def test_retirar_para_mi_nfc(client, session):
    """
    Escenario: Retirada rápida por NFC.
    """
    tech = create_user(session, role="OPERARIO")
    ubi_tech = Ubicacion(nombre="UbiTech", tipo="TECNICO", usuario_id=tech.id)
    session.add(ubi_tech)
    session.commit()
    session.refresh(ubi_tech)

    eq = create_random_equipo(session)
    eq.nfc_tag = "tag_secreto_123"
    session.add(eq)
    session.commit()
    session.refresh(eq)

    headers = get_auth_headers(client, tech.username)

    resp = client.post(
        "/api/v1/movimientos/retirar/me/nfc",
        json={"nfc_tag": "tag_secreto_123"},
        headers=headers,
    )

    assert resp.status_code == 201, resp.text
    session.refresh(eq)
    assert eq.ubicacion_id == ubi_tech.id

# -------------------------------------------------------------------------
# 2. MOVIMIENTOS ESTÁNDAR (Regresión)
# -------------------------------------------------------------------------

def test_movimiento_estandar_almacen_a_laboratorio(client, session):
    """
    Verificar que la lógica antigua de mover entre dos ubicaciones explícitas sigue funcionando.
    """
    admin = create_user(session, role="ADMIN")
    headers = get_auth_headers(client, admin.username)

    almacen = Ubicacion(nombre="Almacén A", tipo="ALMACEN")
    lab = Ubicacion(nombre="Lab B", tipo="LABORATORIO")
    session.add_all([almacen, lab])
    session.commit()
    session.refresh(almacen)
    session.refresh(lab)

    eq = create_random_equipo(session)
    eq.ubicacion_id = almacen.id
    session.add(eq)
    session.commit()
    session.refresh(eq)

    payload = {
        "equipo_id": eq.id,
        "hacia_ubicacion_id": lab.id,
    }
    resp = client.post("/api/v1/movimientos/retirar", json=payload, headers=headers)

    assert resp.status_code == 201, resp.text
    session.refresh(eq)
    assert eq.ubicacion_id == lab.id

# -------------------------------------------------------------------------
# 3. REGLAS DE NEGOCIO (Estados prohibidos)
# -------------------------------------------------------------------------

def test_no_mover_equipo_en_baja(client, session):
    """
    Un equipo dado de BAJA no debería poder moverse.
    """
    tech = create_user(session, role="OPERARIO")
    ubi = Ubicacion(nombre="UbiTech", tipo="TECNICO", usuario_id=tech.id)
    session.add(ubi)
    session.commit()
    session.refresh(ubi)

    eq = create_random_equipo(session, estado="BAJA")

    headers = get_auth_headers(client, tech.username)

    resp = client.post(
        "/api/v1/movimientos/retirar/me",
        json={"equipo_id": eq.id},
        headers=headers,
    )

    assert resp.status_code == 422, resp.text
    assert "estado actual" in resp.json()["detail"]
