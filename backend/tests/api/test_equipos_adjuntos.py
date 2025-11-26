import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.equipo import Equipo
from app.core.file_manager import FileManager
from tests.utils import create_user, get_auth_headers  # <--- IMPORTANTE

@pytest.fixture(autouse=True)
def clean_files(tmp_path):
    original_base = FileManager.BASE_DIR
    FileManager.BASE_DIR = tmp_path
    yield
    FileManager.BASE_DIR = original_base

def test_adjuntos_equipo(client: TestClient, session: Session):
    # 1. Setup Auth
    admin_user = create_user(session, role="ADMIN")
    headers = get_auth_headers(client, admin_user.username)

    # 2. Crear Equipo
    eq = Equipo(identidad="EQ-TEST-DOCS", tipo="Osciloscopio", estado="OPERATIVO")
    session.add(eq)
    session.commit()
    session.refresh(eq)

    # 3. Subir Foto
    file_content = b"fake image bytes"
    files = {
        'file': ('foto_frontal.jpg', file_content, 'image/jpeg')
    }
    
    r = client.post(
        f"/api/v1/equipos/{eq.id}/adjuntos",
        headers=headers,
        files=files
    )
    assert r.status_code == 201
    adjunto_id = r.json()["id"]

    # 4. Listar
    r = client.get(
        f"/api/v1/equipos/{eq.id}/adjuntos",
        headers=headers
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["nombre_archivo"] == "foto_frontal.jpg"

    # 5. Descargar
    r = client.get(
        f"/api/v1/equipos/{eq.id}/adjuntos/{adjunto_id}",
        headers=headers
    )
    assert r.status_code == 200
    assert r.content == file_content

    # 6. Borrar
    r = client.delete(
        f"/api/v1/equipos/{eq.id}/adjuntos/{adjunto_id}",
        headers=headers
    )
    assert r.status_code == 204
    
    # 7. Validar borrado
    r = client.get(f"/api/v1/equipos/{eq.id}/adjuntos", headers=headers)
    assert len(r.json()) == 0