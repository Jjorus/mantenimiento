# backend/app/api/v1/routes_incidencias.py
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response, Request
from pydantic import BaseModel, Field
from typing import Optional, Literal
from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, DBAPIError
from datetime import datetime

from app.core.deps import get_db, current_user, require_role
from app.models.incidencia import Incidencia
from app.models.equipo import Equipo

router = APIRouter(prefix="/incidencias", tags=["incidencias"])

Estado = Literal["ABIERTA", "EN_PROGRESO", "CERRADA"]


# ---------- Schemas ----------
class IncidenciaCreateIn(BaseModel):
    equipo_id: int = Field(..., gt=0, examples=[1])
    titulo: str = Field(..., min_length=3, max_length=150, examples=["Deriva en lectura"])
    descripcion: Optional[str] = Field(None, max_length=2000, examples=["Se observa deriva en canal A"])


class IncidenciaPatchIn(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=2000)
    estado: Optional[Estado] = None


# ---------- Endpoints ----------
@router.post(
    "",
    response_model=Incidencia,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("OPERARIO", "MANTENIMIENTO", "ADMIN"))],
)
def crear_incidencia(
    payload: IncidenciaCreateIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Crear una incidencia (estado por defecto: ABIERTA).
    Registra usuario creador si el modelo lo soporta.
    """
    try:
        eq = db.get(Equipo, payload.equipo_id)
        if not eq:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")

        inc = Incidencia(
            equipo_id=eq.id,
            titulo=payload.titulo,
            descripcion=payload.descripcion,
        )
        if hasattr(Incidencia, "usuario_id"):
            setattr(inc, "usuario_id", int(user["id"]))

        db.add(inc)
        db.commit()
        db.refresh(inc)

        base_url = str(request.base_url).rstrip("/")
        response.headers["Location"] = f"{base_url}/api/v1/incidencias/{inc.id}"
        response.headers["Cache-Control"] = "no-store"
        return inc

    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad en la base de datos")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")


@router.get(
    "",
    response_model=list[Incidencia],
    dependencies=[Depends(current_user)],
)
def listar_incidencias(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados (1-200)"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    estado: Optional[Estado] = Query(None, description="Filtrar por estado"),
    equipo_id: Optional[int] = Query(None, gt=0, description="Filtrar por ID de equipo"),
    desde: datetime | None = Query(None, description="Desde fecha (ISO-8601, UTC)"),
    hasta: datetime | None = Query(None, description="Hasta fecha (ISO-8601, UTC)"),
):
    """
    Listar incidencias con filtros y paginación.
    Devuelve cabecera `X-Total-Count` con el total sin paginar.
    """
    if desde and hasta and desde > hasta:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rango de fechas inválido (desde > hasta)")

    total_stmt = select(func.count()).select_from(Incidencia)
    data_stmt = select(Incidencia)

    conds = []
    if estado:
        conds.append(Incidencia.estado == estado)
    if equipo_id:
        conds.append(Incidencia.equipo_id == equipo_id)
    if desde:
        conds.append(Incidencia.fecha >= desde)
    if hasta:
        conds.append(Incidencia.fecha <= hasta)

    if conds:
        total_stmt = total_stmt.where(*conds)
        data_stmt = data_stmt.where(*conds)

    total = db.exec(total_stmt).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    data_stmt = data_stmt.order_by(Incidencia.fecha.desc()).limit(limit).offset(offset)
    return db.exec(data_stmt).all()


@router.get(
    "/{incidencia_id}",
    response_model=Incidencia,
    dependencies=[Depends(current_user)],
)
def obtener_incidencia(incidencia_id: int, db: Session = Depends(get_db)):
    """
    Obtener una incidencia por ID (autenticado).
    """
    obj = db.get(Incidencia, incidencia_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")
    return obj


@router.patch(
    "/{incidencia_id}",
    response_model=Incidencia,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def actualizar_incidencia(
    incidencia_id: int,
    payload: IncidenciaPatchIn,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Actualizar campos de una incidencia (solo MANTENIMIENTO/ADMIN).
    Usa reglas de dominio para transiciones de estado: cerrar() / reabrir().
    """
    try:
        obj = db.get(Incidencia, incidencia_id)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")

        changed = False

        # cambios de contenido
        if payload.titulo is not None:
            if not payload.titulo.strip():
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El título no puede estar vacío")
            obj.titulo = payload.titulo
            changed = True
        if payload.descripcion is not None:
            obj.descripcion = payload.descripcion
            changed = True

        # transición de estado (aplica métodos de dominio)
        if payload.estado is not None:
            estado_actual = obj.estado
            estado_nuevo = payload.estado

            if estado_nuevo == "CERRADA" and estado_actual != "CERRADA":
                obj.cerrar(int(user["id"]))
                changed = True
            elif estado_nuevo in {"ABIERTA", "EN_PROGRESO"} and estado_actual == "CERRADA":
                obj.reabrir(int(user["id"]))
                changed = True
            elif estado_nuevo != estado_actual:
                obj.estado = estado_nuevo
                if hasattr(Incidencia, "usuario_modificador_id"):
                    obj.usuario_modificador_id = int(user["id"])
                changed = True

        if not changed:
            return obj  # 200 OK, sin cambios

        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    except ValueError as e:
        # errores de reglas de dominio (p.ej., cerrar dos veces)
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad en la base de datos")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")


@router.post(
    "/{incidencia_id}/cerrar",
    response_model=Incidencia,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def cerrar_incidencia(
    incidencia_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Cierra una incidencia aplicando reglas de dominio y auditoría.
    """
    try:
        obj = db.get(Incidencia, incidencia_id)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")
        
        obj.cerrar(int(user["id"]))
        db.add(obj)
        db.commit()
        db.refresh(obj)

        base_url = str(request.base_url).rstrip("/")
        response.headers["Location"] = f"{base_url}/api/v1/incidencias/{obj.id}"
        response.headers["Cache-Control"] = "no-store"
        return obj

    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad en la base de datos")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")


@router.post(
    "/{incidencia_id}/reabrir",
    response_model=Incidencia,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def reabrir_incidencia(
    incidencia_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Reabre una incidencia cerrada aplicando reglas de dominio y auditoría.
    """
    try:
        obj = db.get(Incidencia, incidencia_id)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")
        
        obj.reabrir(int(user["id"]))
        db.add(obj)
        db.commit()
        db.refresh(obj)

        base_url = str(request.base_url).rstrip("/")
        response.headers["Location"] = f"{base_url}/api/v1/incidencias/{obj.id}"
        response.headers["Cache-Control"] = "no-store"
        return obj

    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad en la base de datos")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")