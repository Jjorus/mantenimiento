#base.py

from sqlmodel import SQLModel

metadata = SQLModel.metadata


from .seccion import Seccion  # noqa: F401
from .ubicacion import Ubicacion  # noqa: F401
from .equipo import Equipo  # noqa: F401
from .incidencia import Incidencia  # noqa: F401
from .reparacion import Reparacion  # noqa: F401
from .movimiento import Movimiento  # noqa: F401
from .usuario import Usuario  # noqa: F401


__all__ = ["SQLModel", "metadata"]