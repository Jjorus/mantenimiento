# backend/tests/api/test_auth.py
import pytest
from app.models.usuario import Usuario
from sqlmodel import select
from tests.utils import create_user, get_auth_headers, TEST_PASSWORD

# -------------------------------------------------------------------------
# 1. LOGIN EXITOSO (Happy Path & Case Insensitive)
# -------------------------------------------------------------------------

def test_login_success_standard(client, session):
    """
    Verifica el flujo normal: Credenciales correctas devuelven token.
    """
    user = create_user(session, role="OPERARIO")
    
    response = client.post("/api/auth/login", json={
        "username_or_email": user.username,
        "password": TEST_PASSWORD,  # Contraseña por defecto en utils.create_user
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_case_insensitive(client, session):
    """
    Verifica que CITEXT en Postgres funciona:
    Se puede loguear con 'USUARIO' aunque en BD esté 'usuario'.
    """
    user = create_user(session)
    
    response = client.post("/api/auth/login", json={
        "username_or_email": user.username.upper(),
        "password": TEST_PASSWORD,
    })
    
    assert response.status_code == 200
    assert "access_token" in response.json()

# -------------------------------------------------------------------------
# 2. LOGIN FALLIDO (Sad Path)
# -------------------------------------------------------------------------

def test_login_wrong_password(client, session):
    """Verifica que contraseña incorrecta devuelve 401."""
    user = create_user(session)
    
    response = client.post("/api/auth/login", json={
        "username_or_email": user.username,
        "password": "WRONG_PASSWORD_123",
    })
    
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower() or "inválid" in response.json()["detail"].lower()


def test_login_non_existent_user(client, session):
    """Verifica que usuario inexistente devuelve 401 (no 404 por seguridad)."""
    response = client.post("/api/auth/login", json={
        "username_or_email": "fantasma_no_existe",
        "password": TEST_PASSWORD,
    })
    assert response.status_code == 401

# -------------------------------------------------------------------------
# 3. RATE LIMITING (Protección Fuerza Bruta con Redis)
# -------------------------------------------------------------------------

def test_rate_limit_brute_force(client, session, redis_client):
    """
    Verifica que Redis bloquea tras N intentos fallidos.
    NOTA: Depende de la config de rate-limit en tu backend.
    """
    user = create_user(session)
    
    blocked = False
    resp = None
    for _ in range(15):
        resp = client.post("/api/auth/login", json={
            "username_or_email": user.username,
            "password": "BAD_PASSWORD",
        })
        if resp.status_code == 429:
            blocked = True
            break
    
    assert blocked is True, "El sistema no bloqueó tras múltiples intentos fallidos"
    
    data = resp.json()
    # Adapta esta cadena a tu mensaje real de error
    assert "demasiados intentos" in data["detail"].lower() or "too many" in data["detail"].lower()

# -------------------------------------------------------------------------
# 4. RBAC (Control de Roles)
# -------------------------------------------------------------------------

def test_rbac_operario_cannot_delete_user(client, session):
    """
    Verifica que un OPERARIO recibe 403 al intentar acceder
    a un endpoint protegido solo para ADMIN.
    Endpoint probado: DELETE /api/v1/usuarios/{id}
    """
    attacker = create_user(session, role="OPERARIO")
    victim = create_user(session, role="OPERARIO")
    
    headers = get_auth_headers(client, attacker.username)
    
    response = client.delete(f"/api/v1/usuarios/{victim.id}", headers=headers)
    
    assert response.status_code == 403
    assert "no autorizado" in response.json()["detail"].lower() or "forbidden" in response.json()["detail"].lower()


def test_rbac_admin_can_access_protected(client, session):
    """
    Verifica que un ADMIN sí puede acceder a endpoints protegidos.
    Endpoint probado: GET /api/v1/usuarios/{id}
    """
    admin = create_user(session, role="ADMIN")
    target = create_user(session, role="OPERARIO")
    
    headers = get_auth_headers(client, admin.username)
    
    response = client.get(f"/api/v1/usuarios/{target.id}", headers=headers)
    
    assert response.status_code == 200
    assert response.json()["username"] == target.username
