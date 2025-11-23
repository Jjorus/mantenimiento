import os
import time
from pathlib import Path

import pytest
import redis
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, text
from sqlalchemy import exc, event
from sqlalchemy.orm import sessionmaker

# --------------------------------------------------------------------
# 1) Cargar .env.test y forzar entorno de TEST
# --------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]  # carpeta backend/
TEST_ENV_PATH = BASE_DIR / ".env.test"

if TEST_ENV_PATH.exists():
    # Carga TODAS las variables de .env.test en el entorno
    load_dotenv(TEST_ENV_PATH, override=True)

# Seguridad: comprobamos que APP_ENV=test
os.environ.setdefault("APP_ENV", "test")
if os.getenv("APP_ENV") != "test":
    raise RuntimeError("¡PELIGRO! APP_ENV no es 'test'. Revisa .env.test y conftest.py")

# Valores por defecto razonables POR SI acaso faltan en .env.test
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:test_password@localhost:5433/mant_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("TRUSTED_HOSTS", "testserver,localhost,127.0.0.1")

# --------------------------------------------------------------------
# 2) Importar app y utilidades de tu backend (ya con entorno de test)
# --------------------------------------------------------------------
from app.main import app  # noqa: E402
from app.core.db import get_engine, get_session  # noqa: E402
from app.core.deps import get_db  # noqa: E402
from app.core.config import settings  # noqa: E402
from seeds.seed_dev import run as seed_dev_run  # noqa: E402

# Usamos el engine oficial de la app
engine = get_engine()

# Session factory para tests, usando la clase Session de SQLModel
TestingSessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


# --------------------------------------------------------------------
# 3) Esperar a que Postgres y Redis estén listos
# --------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """Espera activa hasta que la BD y Redis contestan."""
    # Esperar DB
    for _ in range(40):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except (exc.OperationalError, exc.DatabaseError):
            time.sleep(0.5)

    # Esperar Redis
    r = redis.from_url(settings.REDIS_URL)
    for _ in range(40):
        try:
            if r.ping():
                break
        except redis.ConnectionError:
            time.sleep(0.5)
    r.close()


# --------------------------------------------------------------------
# 4) Esquema y datos base (CITEXT + tablas + seed_dev)
# --------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def setup_db_schema(wait_for_services):
    """
    - Crea la extensión CITEXT (necesaria para Usuario, etc.).
    - Crea todas las tablas (SQLModel.metadata.create_all).
    - Ejecuta seed_dev (admin, ubicaciones, equipos base).
    """
    import app.models  # registra modelos en SQLModel.metadata

    # Extensión CITEXT (Postgres)
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        connection.commit()

    # Crear tablas
    SQLModel.metadata.create_all(engine)

    # Seed de datos base (fuera de las transacciones de cada test)
    with Session(engine) as s:
        seed_dev_run()

    yield

    # Al terminar TODA la sesión de tests, limpiar
    SQLModel.metadata.drop_all(engine)


# --------------------------------------------------------------------
# 5) Sesión de BD por test con transacción anidada (SAVEPOINT)
#    -> garantiza ROLLBACK incluso si el código hace db.commit()
# --------------------------------------------------------------------
@pytest.fixture(name="session")
def session_fixture():
    """
    - Abre una conexión y una transacción externa.
    - Crea una sesión SQLAlchemy/SQLModel ligada a esa conexión.
    - Abre una transacción anidada (SAVEPOINT).
    - Cualquier db.commit() dentro del código sólo afecta al SAVEPOINT.
    - Al final del test, se hace rollback de la transacción externa
      => la BD queda como al inicio del test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # SAVEPOINT inicial
    nested = session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        """
        Cada vez que termina la transacción anidada (por commit/rollback),
        si la transacción externa sigue activa, creamos un nuevo SAVEPOINT.
        Esto permite múltiples db.commit() dentro del mismo test.
        """
        nonlocal nested
        if trans is nested and transaction.is_active:
            nested = sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# --------------------------------------------------------------------
# 6) Cliente Redis de test (flushdb por test)
# --------------------------------------------------------------------
@pytest.fixture(name="redis_client")
def redis_client_fixture():
    """
    Cliente Redis apuntando al contenedor de test.
    Se hace FLUSHDB tras cada test.
    """
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield r
    finally:
        r.flushdb()
        r.close()


# --------------------------------------------------------------------
# 7) TestClient de FastAPI con overrides de DB y Redis
# --------------------------------------------------------------------
@pytest.fixture(name="client")
def client_fixture(session: Session, redis_client):
    """
    Cliente de tests para la API:
    - Sobrescribe get_session y get_db para usar la 'session' del test.
    - Inyecta redis_client en rate_limit y security.
    """

    # ----- Override de dependencias de BD -----
    def get_session_override():
        try:
            yield session
        finally:
            # el rollback lo hace la fixture 'session'
            pass

    def get_db_override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_db] = get_db_override

    # ----- Inyección de Redis en singletons -----
    import app.core.rate_limit as rate_limit_module
    import app.core.security as security_module

    original_rl_client = getattr(rate_limit_module, "_redis_client", None)
    original_sec_client = getattr(security_module, "_redis_client", None)

    rate_limit_module._redis_client = redis_client
    security_module._redis_client = redis_client

    try:
        with TestClient(app) as c:
            yield c
    finally:
        # Restaurar estado original
        app.dependency_overrides.clear()
        rate_limit_module._redis_client = original_rl_client
        security_module._redis_client = original_sec_client
