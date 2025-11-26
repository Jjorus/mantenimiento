# backend/app/models/__init__.py

from .base import (
    SQLModel,
    metadata,
    Seccion,
    Ubicacion,
    Equipo,
    Incidencia,
    Reparacion,
    Movimiento,
    Usuario,
)

# Modelos de adjuntos
from .reparacion_factura import ReparacionFactura
from .incidencia_adjunto import IncidenciaAdjunto # Nuevo
from .equipo_adjunto import EquipoAdjunto # Nuevo

__all__ = [
    "SQLModel",
    "metadata",
    "Seccion",
    "Ubicacion",
    "Equipo",
    "Incidencia",
    "Reparacion",
    "Movimiento",
    "Usuario",
    "ReparacionFactura",
    "IncidenciaAdjunto",
    "EquipoAdjunto",
]