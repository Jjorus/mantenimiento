# backend/tests/api/test_usuarios.py
import pytest
from tests.utils import create_user, get_auth_headers, random_string

def test_admin_create_user_con_nombre_apellidos(client, session):
    """
    Verifica que un ADMIN puede crear un usuario con nombre y apellidos.
    """
    admin = create_user(session, role="ADMIN")
    headers = get_auth_headers(client, admin.username)

    new_username = f"u_{random_string(5)}"
    payload = {
        "username": new_username,
        "email": f"{new_username}@test.com",
        "password": "securePassword123",
        "role": "OPERARIO",
        "active": True,
        "nombre": "Juan",           # NUEVO
        "apellidos": "Pérez Gómez"  # NUEVO
    }

    resp = client.post("/api/v1/usuarios", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    
    assert data["username"] == new_username
    assert data["nombre"] == "Juan"
    assert data["apellidos"] == "Pérez Gómez"

def test_admin_update_user_info(client, session):
    """
    Verifica que un ADMIN puede actualizar nombre y apellidos de otro usuario.
    """
    admin = create_user(session, role="ADMIN")
    target_user = create_user(session, role="OPERARIO", nombre="Viejo", apellidos="Nombre")
    
    headers = get_auth_headers(client, admin.username)

    payload = {
        "nombre": "NuevoNombre",
        "apellidos": "NuevoApellido"
    }

    resp = client.patch(f"/api/v1/usuarios/{target_user.id}", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["nombre"] == "NuevoNombre"
    assert data["apellidos"] == "NuevoApellido"
    # Verificar que no se han borrado otros datos
    assert data["username"] == target_user.username

def test_me_endpoint_returns_full_info(client, session):
    """
    Verifica que el endpoint /me devuelve los nuevos campos.
    """
    user = create_user(session, role="OPERARIO", nombre="Self", apellidos="Test")
    headers = get_auth_headers(client, user.username)

    resp = client.get("/api/v1/usuarios/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["nombre"] == "Self"
    assert data["apellidos"] == "Test"