# backend/app/core/file_manager.py
import shutil
from pathlib import Path
from uuid import uuid4
from typing import Optional, Set
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

class FileManager:
    """
    Gestor centralizado para subir, recuperar y borrar archivos.
    Utiliza FACTURAS_DIR como base, creando subcarpetas dentro.
    """
    
    # Directorio base definido en config.py
    BASE_DIR = Path(settings.FACTURAS_DIR).resolve()

    # LISTA AMPLIADA: Documentos de oficina, texto e imágenes.
    ALLOWED_MIMES = {
        # Imágenes
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        
        # Documentos PDF
        "application/pdf",
        
        # Texto
        "text/plain",
        "text/csv",
        
        # Microsoft Word
        "application/msword", # .doc
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # .docx
        
        # Microsoft Excel
        "application/vnd.ms-excel", # .xls
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", # .xlsx
        
        # OpenOffice / LibreOffice
        "application/vnd.oasis.opendocument.text", # .odt
        "application/vnd.oasis.opendocument.spreadsheet", # .ods
    }
    
    MAX_SIZE_MB = 20

    @classmethod
    def validate_file(cls, file: UploadFile):
        if not file.filename:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El archivo no tiene nombre")
        
        # Validación de seguridad: Bloquear ejecutables y scripts
        if file.content_type not in cls.ALLOWED_MIMES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Tipo de archivo no permitido ({file.content_type})"
            )

    @classmethod
    async def save_file(cls, file: UploadFile, subfolder: str, prefix: str) -> dict:
        """
        Guarda un archivo en disco.
        Retorna dict con: relative_path, filename, size_bytes, content_type
        """
        cls.validate_file(file)
        
        # Estructura: BASE_DIR / subfolder / archivo
        folder_path = cls.BASE_DIR / subfolder
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Generar nombre único
        orig = file.filename or "unknown"
        # Limpiar nombre original de caracteres raros
        safe_orig = Path(orig).name
        
        ext = Path(safe_orig).suffix or ""
        uid = uuid4().hex
        
        # Ejemplo: inc_45_a1b2c3d4.jpg
        safe_filename = f"{prefix}_{uid}{ext}"
        
        file_path = folder_path / safe_filename
        
        # Guardar (Streaming)
        size_bytes = 0
        max_bytes = cls.MAX_SIZE_MB * 1024 * 1024
        
        try:
            with file_path.open("wb") as buffer:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    if size_bytes > max_bytes:
                        buffer.close()
                        file_path.unlink(missing_ok=True)
                        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Archivo demasiado grande")
                    buffer.write(chunk)
        except Exception as e:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                pass
                
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error al guardar archivo en disco")
            
        return {
            "nombre_archivo": safe_orig,
            "ruta_relativa": f"{subfolder}/{safe_filename}",
            "tamano_bytes": size_bytes,
            "content_type": file.content_type
        }

    @classmethod
    def get_path(cls, relative_path: str) -> Path:
        """Devuelve Path absoluto."""
        return cls.BASE_DIR / relative_path

    @classmethod
    def delete_file(cls, relative_path: str):
        """Borra el archivo físico."""
        if not relative_path:
            return
        path = cls.get_path(relative_path)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass