# opcional: solo re-exporta para ergonomía
from __future__ import annotations

from .base import (
    SQLModel, metadata,
    Seccion, Ubicacion, Equipo, Incidencia, Reparacion, Movimiento, Usuario,
)
__all__ = ["SQLModel", "metadata", "Seccion", "Ubicacion", "Equipo",
           "Incidencia", "Reparacion", "Movimiento", "Usuario"]
