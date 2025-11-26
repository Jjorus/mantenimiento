import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.incidencia import Incidencia
from app.models.equipo import Equipo
from app.core.file_manager import FileManager
from tests.utils import create_user, get_auth_headers  # <--- IMPORTANTE: Usar tus helpers

@pytest.fixture(autouse=True)
def clean_files(tmp_path):
    original_base = FileManager.BASE_DIR
    FileManager.BASE_DIR = tmp_path
    yield
    FileManager.BASE_DIR = original_base

def test_ciclo_adjuntos_incidencia(client: TestClient, session: Session):
    # 1. Setup Auth: Crear usuario admin y obtener headers
    # Usamos 'MANTENIMIENTO' o 'ADMIN' que tienen permiso
    admin_user = create_user(session, role="ADMIN")
    headers = get_auth_headers(client, admin_user.username)

    # 2. Setup Data
    eq = Equipo(identidad="EQ-TEST-INC-ADJ", tipo="Generador", estado="OPERATIVO")
    session.add(eq)
    session.commit()
    session.refresh(eq)
    
    inc = Incidencia(equipo_id=eq.id, titulo="Test Adjuntos", estado="ABIERTA")
    session.add(inc)
    session.commit()
    session.refresh(inc)

    # 3. Subir archivo
    file_content = b"%PDF-1.4 mock content"
    files = {
        'file': ('manual_error.pdf', file_content, 'application/pdf')
    }
    
    r = client.post(
        f"/api/v1/incidencias/{inc.id}/adjuntos",
        headers=headers,  # Usamos los headers generados
        files=files
    )
    assert r.status_code == 201
    data = r.json()
    assert data["nombre_archivo"] == "manual_error.pdf"
    adjunto_id = data["id"]

    # 4. Listar
    r = client.get(
        f"/api/v1/incidencias/{inc.id}/adjuntos",
        headers=headers
    )
    assert r.status_code == 200
    lista = r.json()
    assert len(lista) == 1
    assert lista[0]["id"] == adjunto_id

    # 5. Descargar
    r = client.get(
        f"/api/v1/incidencias/{inc.id}/adjuntos/{adjunto_id}",
        headers=headers
    )
    assert r.status_code == 200
    assert r.content == file_content
    assert r.headers["content-type"] == "application/pdf"

    # 6. Eliminar
    r = client.delete(
        f"/api/v1/incidencias/{inc.id}/adjuntos/{adjunto_id}",
        headers=headers
    )
    assert r.status_code == 204
    
    # Verificar borrado
    r = client.get(f"/api/v1/incidencias/{inc.id}/adjuntos", headers=headers)
    assert len(r.json()) == 0