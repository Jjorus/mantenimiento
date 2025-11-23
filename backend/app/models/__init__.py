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

# Importamos explícitamente el nuevo modelo de facturas de reparación
from .reparacion_factura import ReparacionFactura

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
]
