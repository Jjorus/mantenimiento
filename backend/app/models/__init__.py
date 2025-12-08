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
# ... importaciones existentes ...
from .reparacion import Reparacion
from .reparacion_factura import ReparacionFactura
from .incidencia_adjunto import IncidenciaAdjunto # Nuevo
from .equipo_adjunto import EquipoAdjunto # Nuevo
from .usuario_adjunto import UsuarioAdjunto  # Nuevo
from .reparacion_gasto import ReparacionGasto

__all__ = [
    "SQLModel",
    "metadata",
    "Seccion",
    "Ubicacion",
    "Equipo",
    "Incidencia",
    "Reparacion",
    "ReparacionGasto",
    "Movimiento",
    "Usuario",
    "ReparacionFactura",
    "IncidenciaAdjunto",
    "EquipoAdjunto",
    "UsuarioAdjunto",
]