# backend/tests/utils.py
import random
import string
from sqlmodel import Session

from app.models.usuario import Usuario
from app.models.equipo import Equipo
from app.core.security import hash_password

# Contraseña única para todos los tests
TEST_PASSWORD = "password123"


def random_string(k: int = 8) -> str:
    """Cadena aleatoria para identidad, serie, etc."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=k))


def create_user(
    session: Session, 
    role: str = "OPERARIO", 
    active: bool = True,
    nombre: str = None,      # NUEVO
    apellidos: str = None    # NUEVO
) -> Usuario:
    """
    Crea un usuario de test en la BD y lo devuelve.
    Usa TEST_PASSWORD como contraseña.
    """
    username = f"u_{random_string(6)}"
    email = f"{username.lower()}@example.com"

    user = Usuario(
        username=username,
        email=email,
        password_hash=hash_password(TEST_PASSWORD),
        role=role,
        active=active,
        nombre=nombre,          # NUEVO
        apellidos=apellidos,    # NUEVO
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_auth_headers(client, username: str, password: str = TEST_PASSWORD) -> dict:
    """
    Hace login contra /api/auth/login y devuelve el header Authorization listo.
    Lanza assert si el login falla.
    """
    resp = client.post(
        "/api/auth/login",
        json={
            "username_or_email": username,
            "password": password,
        },
    )
    assert resp.status_code == 200, f"Login falló para {username}: {resp.text}"
    data = resp.json()
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_random_equipo(
    session: Session,
    tipo: str = "GENÉRICO",
    estado: str = "OPERATIVO",
) -> Equipo:
    identidad = f"EQ-{random_string(6)}"
    numero_serie = f"SN-{random_string(6)}"

    eq = Equipo(
        identidad=identidad,
        numero_serie=numero_serie,
        tipo=tipo,
        estado=estado,
    )
    session.add(eq)
    session.commit()
    session.refresh(eq)
    return eq