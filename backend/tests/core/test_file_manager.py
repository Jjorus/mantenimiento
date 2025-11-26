# backend/tests/core/test_file_manager.py
import pytest
from io import BytesIO
from fastapi import UploadFile, HTTPException
from app.core.file_manager import FileManager

# --- FIX: Forzar uso de asyncio solamente (evita error de 'trio') ---
@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_validate_file_invalid_mime():
    # FIX: 'file' es obligatorio en UploadFile. Usamos BytesIO para simularlo.
    file = UploadFile(
        file=BytesIO(b"fake content"), 
        filename="test.exe", 
        headers={"content-type": "application/x-msdownload"}
    )
    
    with pytest.raises(HTTPException) as exc:
        FileManager.validate_file(file)
    assert exc.value.status_code == 422

@pytest.mark.anyio
async def test_save_and_delete_file(tmp_path):
    # Mockear BASE_DIR
    FileManager.BASE_DIR = tmp_path
    
    content = b"fake pdf content"
    filename = "doc_prueba.pdf"
    
    # FIX: Pasamos el 'file' correctamente simulado
    file = UploadFile(
        file=BytesIO(content), 
        filename=filename, 
        headers={"content-type": "application/pdf"}
    )
    
    # Test Save
    result = await FileManager.save_file(file, "test_folder", "prefix")
    
    assert result["nombre_archivo"] == filename
    assert (tmp_path / result["ruta_relativa"]).exists()
    
    # Test Delete
    FileManager.delete_file(result["ruta_relativa"])
    assert not (tmp_path / result["ruta_relativa"]).exists()