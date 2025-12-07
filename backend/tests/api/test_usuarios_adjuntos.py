# backend/tests/api/test_usuarios_adjuntos.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.file_manager import FileManager
from app.models.usuario import Usuario
from tests.utils import create_user, get_auth_headers


@pytest.fixture(autouse=True)
def clean_files(tmp_path):
    """
    Hace que todos los tests de este módulo usen un directorio temporal
    como base para FileManager, para no ensuciar el sistema de ficheros real.
    """
    original_base = FileManager.BASE_DIR
    FileManager.BASE_DIR = tmp_path
    try:
        yield
    finally:
        FileManager.BASE_DIR = original_base


def test_actualizar_notas_usuario(client: TestClient, session: Session):
    """
    Un ADMIN puede actualizar las notas internas de un usuario
    mediante PATCH /api/v1/usuarios/{id}/notas y quedan persistidas en BD.
    """
    # 1) Creamos un admin y un usuario objetivo
    admin = create_user(session, role="ADMIN")
    target = create_user(session, role="OPERARIO")
    headers = get_auth_headers(client, admin.username)

    notas_texto = "Notas internas de prueba"

    # 2) Llamamos al endpoint de notas
    resp = client.patch(
        f"/api/v1/usuarios/{target.id}/notas",
        json={"notas": notas_texto},
        headers=headers,
    )

    assert resp.status_code == 204

    # 3) Verificamos en BD que se ha guardado correctamente
    refreshed = session.get(Usuario, target.id)
    assert refreshed is not None
    assert refreshed.notas == notas_texto


def test_ciclo_adjuntos_usuario(client: TestClient, session: Session):
    """
    Ciclo completo de adjuntos de usuario:
    - Subir fichero
    - Listar
    - Descargar
    - Borrar
    - Verificar que la lista queda vacía
    """
    # 1) Admin y usuario objetivo
    admin = create_user(session, role="ADMIN")
    target = create_user(session, role="OPERARIO")
    headers = get_auth_headers(client, admin.username)

    # 2) Preparamos un "archivo" en memoria
    file_content = b"contenido de prueba de usuario"
    file_name = "usuario_test.txt"

    # 3) Subir adjunto
    resp = client.post(
        f"/api/v1/usuarios/{target.id}/adjuntos",
        files={"file": (file_name, file_content, "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 201

    data = resp.json()
    assert data["nombre_archivo"] == file_name
    assert "id" in data
    adjunto_id = data["id"]

    # 4) Listar adjuntos
    resp = client.get(
        f"/api/v1/usuarios/{target.id}/adjuntos",
        headers=headers,
    )
    assert resp.status_code == 200
    lista = resp.json()

    assert isinstance(lista, list)
    assert len(lista) == 1
    assert lista[0]["id"] == adjunto_id
    assert lista[0]["nombre_archivo"] == file_name
    # La URL debe apuntar al endpoint de descarga
    assert f"/api/v1/usuarios/{target.id}/adjuntos/{adjunto_id}" in lista[0]["url"]

    # 5) Descargar adjunto
    resp = client.get(
        f"/api/v1/usuarios/{target.id}/adjuntos/{adjunto_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.content == file_content
    # content-type viene del UploadFile ("text/plain")
    assert resp.headers["content-type"].startswith("text/plain")

    # 6) Borrar adjunto
    resp = client.delete(
        f"/api/v1/usuarios/{target.id}/adjuntos/{adjunto_id}",
        headers=headers,
    )
    assert resp.status_code == 204

    # 7) Comprobar que ya no hay adjuntos
    resp = client.get(
        f"/api/v1/usuarios/{target.id}/adjuntos",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []
