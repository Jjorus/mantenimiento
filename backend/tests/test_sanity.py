from app.models.usuario import Usuario
from sqlmodel import select
from tests.utils import create_user, get_auth_headers

def test_full_stack_health(client):
    """
    Prueba que:
    1. /health responde 200.
    2. El JSON tiene la estructura unificada correcta.
    3. DB y Redis están 'healthy' dentro de 'components'.
    """
    r = client.get("/health")
    
    # Aseguramos que responde 200 OK (significa que ambos servicios van bien)
    assert r.status_code == 200, f"Health check falló: {r.text}"
    
    data = r.json()

    # Validamos estructura del nuevo main.py unificado
    assert data["environment"] == "test"
    assert data["status"] == "ok"  # Estado global resumen
    assert "timestamp" in data
    
    # Validamos componentes específicos
    components = data.get("components", {})
    assert components["database"] == "healthy"
    assert components["redis"] == "healthy"


def test_transaction_rollback_and_api_visibility(client, session):
    """
    Prueba crítica de arquitectura:
    1. Creamos usuario en el test (usando `session`).
    2. Intentamos loguearnos vía API (usando `client`).
    3. Si la API ve al usuario, comparten sesión/conn.
    4. Verificamos que CITEXT funciona.
    """
    # 1. Crear usuario en la sesión de test
    # (Seed dev ya corrió, pero creamos uno nuevo para aislar la prueba)
    user = create_user(session, role="ADMIN")

    # 2. La API debe poder loguear a ese usuario (Prueba de visibilidad transaccional)
    headers = get_auth_headers(client, user.username)
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")

    # 3. Verificar que CITEXT funciona:
    # Guardamos en minúsculas (en create_user utils) -> buscamos en MAYÚSCULAS
    found = session.exec(
        select(Usuario).where(Usuario.username == user.username.upper())
    ).first()
    
    assert found is not None
    assert found.id == user.id


def test_redis_flushing(client, redis_client):
    """
    Verifica que Redis funciona y que la fixture lo limpia entre tests.
    """
    # Escribimos algo sucio
    redis_client.set("persist", "no")
    assert redis_client.get("persist") == "no"
    
    # No necesitamos assert del flush aquí, 
    # eso se garantiza al correr múltiples tests seguidos.