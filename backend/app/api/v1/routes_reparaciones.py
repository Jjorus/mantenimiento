# backend/app/api/v1/routes_reparaciones.py
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func, select as sa_select
from sqlalchemy.exc import IntegrityError, DBAPIError, OperationalError

from app.core.deps import get_db, current_user, require_role
from app.models.equipo import Equipo
from app.models.reparacion import Reparacion

router = APIRouter(prefix="/reparaciones", tags=["reparaciones"])

# ----------------- Constantes / helpers -----------------
EstadoReparacion = Literal["ABIERTA", "EN_PROCESO", "CERRADA"]
ALLOWED_ORDEN = {
    "id_asc", "id_desc",
    "inicio_asc", "inicio_desc",
    "estado_asc", "estado_desc",
}

def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s2 = s.strip()
    return s2 if s2 else None

def _raise_422(errors: List[Dict[str, Any]]) -> None:
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

def _validar_estado_transicion(actual: str, nuevo: str, errors: List[Dict[str, Any]]) -> None:
    # No permitir pasar de CERRADA a otro estado por aquí (usar /reabrir)
    if actual == "CERRADA" and nuevo != "CERRADA":
        errors.append({
            "loc": ["body", "estado"],
            "msg": "No se puede reabrir una reparación cerrada desde este endpoint. Usa /{id}/reabrir",
            "type": "value_error"
        })
    if actual == "ABIERTA" and nuevo not in {"ABIERTA", "EN_PROCESO", "CERRADA"}:
        errors.append({"loc": ["body", "estado"], "msg": "Transición inválida", "type": "value_error"})
    if actual == "EN_PROCESO" and nuevo not in {"EN_PROCESO", "CERRADA"}:
        errors.append({"loc": ["body", "estado"], "msg": "Transición inválida", "type": "value_error"})

# ----------------- Schemas -----------------
class ReparacionCreateIn(BaseModel):
    equipo_id: int = Field(..., gt=0, examples=[1])
    titulo: str = Field(..., min_length=3, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=8000)
    # opcionalmente permitir abrir ya EN_PROCESO
    estado: Optional[EstadoReparacion] = Field(None, examples=["ABIERTA"])

class ReparacionUpdateIn(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=8000)
    estado: Optional[EstadoReparacion] = Field(None)

class ReparacionCerrarIn(BaseModel):
    fecha_fin: Optional[datetime] = Field(None, description="Si no se envía, se usa 'now()' (UTC)")

# ----------------- Endpoints -----------------
@router.post(
    "",
    response_model=Reparacion,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def crear_reparacion(
    payload: ReparacionCreateIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    errors: List[Dict[str, Any]] = []

    equipo = db.get(Equipo, payload.equipo_id)
    if not equipo:
        errors.append({"loc": ["body", "equipo_id"], "msg": "Equipo inexistente", "type": "value_error.foreign_key"})

    estado = payload.estado or "ABIERTA"
    # No permitir crear directamente 'CERRADA'
    if estado not in {"ABIERTA", "EN_PROCESO"}:
        errors.append({"loc": ["body", "estado"], "msg": "Estado inicial inválido", "type": "value_error"})

    if errors:
        _raise_422(errors)

    rep = Reparacion(
        equipo_id=payload.equipo_id,
        titulo=_norm(payload.titulo),
        descripcion=_norm(payload.descripcion),
        estado=estado,
        usuario_id=int(user["id"]) if user and user.get("id") else None,
    )

    try:
        db.add(rep)
        db.commit()
        db.refresh(rep)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad (FK/índices)")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")

    base_url = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base_url}/api/v1/reparaciones/{rep.id}"
    response.headers["Cache-Control"] = "no-store"
    return rep


@router.get(
    "",
    response_model=list[Reparacion],
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def listar_reparaciones(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None, description="Buscar en título (ILIKE)"),
    equipo_id: Optional[int] = Query(None, gt=0),
    estado: Optional[EstadoReparacion] = Query(None),
    estados: Optional[str] = Query(None, description="Estados separados por coma"),
    desde: Optional[datetime] = Query(None, description="Fecha inicio >= (ISO-8601, UTC)"),
    hasta: Optional[datetime] = Query(None, description="Fecha inicio <= (ISO-8601, UTC)"),
    ordenar: str = Query("inicio_desc", description="id_asc|id_desc|inicio_asc|inicio_desc|estado_asc|estado_desc"),
):
    if ordenar not in ALLOWED_ORDEN:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{"loc": ["query", "ordenar"], "msg": f"Orden inválido. Válidos: {', '.join(sorted(ALLOWED_ORDEN))}", "type": "value_error"}],
        )
    if desde and hasta and desde > hasta:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Rango de fechas inválido (desde > hasta)")

    stmt = select(Reparacion)
    count_stmt = select(func.count()).select_from(Reparacion)

    conds = []
    if q:
        like = f"%{q}%"
        conds.append(Reparacion.titulo.ilike(like))
    if equipo_id:
        conds.append(Reparacion.equipo_id == equipo_id)
    if estado:
        conds.append(Reparacion.estado == estado)
    if estados:
        lista = [e.strip().upper() for e in estados.split(",") if e.strip()]
        validos = [e for e in lista if e in EstadoReparacion.__args__]
        if validos:
            conds.append(Reparacion.estado.in_(validos))
    if desde:
        conds.append(Reparacion.fecha_inicio >= desde)
    if hasta:
        conds.append(Reparacion.fecha_inicio <= hasta)

    if conds:
        stmt = stmt.where(*conds)
        count_stmt = count_stmt.where(*conds)

    # orden
    if ordenar == "id_asc":
        stmt = stmt.order_by(Reparacion.id.asc())
    elif ordenar == "id_desc":
        stmt = stmt.order_by(Reparacion.id.desc())
    elif ordenar == "estado_asc":
        stmt = stmt.order_by(Reparacion.estado.asc(), Reparacion.fecha_inicio.desc())
    elif ordenar == "estado_desc":
        stmt = stmt.order_by(Reparacion.estado.desc(), Reparacion.fecha_inicio.desc())
    elif ordenar == "inicio_asc":
        stmt = stmt.order_by(Reparacion.fecha_inicio.asc())
    else:  # inicio_desc
        stmt = stmt.order_by(Reparacion.fecha_inicio.desc())

    total = db.exec(count_stmt).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    stmt = stmt.limit(limit).offset(offset)
    return db.exec(stmt).all()


@router.get(
    "/{reparacion_id}",
    response_model=Reparacion,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def obtener_reparacion(reparacion_id: int, db: Session = Depends(get_db)):
    rep = db.get(Reparacion, reparacion_id)
    if not rep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparación no encontrada")
    return rep


@router.get(
    "/equipo/{equipo_id}",
    response_model=list[Reparacion],
    response_model_exclude_none=True,
    dependencies=[Depends(current_user)],
)
def listar_por_equipo(
    equipo_id: int,
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")

    total = db.exec(
        select(func.count()).select_from(Reparacion).where(Reparacion.equipo_id == equipo_id)
    ).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    stmt = (
        select(Reparacion)
        .where(Reparacion.equipo_id == equipo_id)
        .order_by(Reparacion.fecha_inicio.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.exec(stmt).all()


@router.patch(
    "/{reparacion_id}",
    response_model=Reparacion,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def actualizar_reparacion(
    reparacion_id: int,
    payload: ReparacionUpdateIn,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    rep = db.get(Reparacion, reparacion_id)
    if not rep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparación no encontrada")

    errors: List[Dict[str, Any]] = []

    if payload.estado is not None:
        _validar_estado_transicion(rep.estado, payload.estado, errors)
    if errors:
        _raise_422(errors)

    try:
        with db.begin():
            rep_db = db.exec(
                sa_select(Reparacion).where(Reparacion.id == rep.id).with_for_update()
            ).scalar_one()

            if payload.titulo is not None:
                rep_db.titulo = _norm(payload.titulo)
            if payload.descripcion is not None:
                rep_db.descripcion = _norm(payload.descripcion)

            if payload.estado is not None and payload.estado != rep_db.estado:
                # Cierre por endpoint dedicado
                if payload.estado == "CERRADA":
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "Para cerrar una reparación usa el endpoint /{id}/cerrar",
                    )
                rep_db.estado = payload.estado

            if hasattr(rep_db, "usuario_modificador_id") and user and user.get("id"):
                rep_db.usuario_modificador_id = int(user["id"])

            db.add(rep_db)
            db.flush()
            db.refresh(rep_db)
            return rep_db

    except OperationalError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Error temporal de base de datos")
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad")
    except DBAPIError:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")


@router.post(
    "/{reparacion_id}/cerrar",
    response_model=Reparacion,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def cerrar_reparacion(
    reparacion_id: int,
    payload: ReparacionCerrarIn,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    rep = db.get(Reparacion, reparacion_id)
    if not rep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparación no encontrada")

    if rep.estado == "CERRADA":
        # idempotente
        return rep

    fecha_fin = payload.fecha_fin or datetime.now(timezone.utc)
    if rep.fecha_inicio and fecha_fin < rep.fecha_inicio:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "fecha_fin no puede ser anterior a fecha_inicio")

    try:
        with db.begin():
            rep_db = db.exec(
                sa_select(Reparacion).where(Reparacion.id == rep.id).with_for_update()
            ).scalar_one()
            rep_db.estado = "CERRADA"
            rep_db.fecha_fin = fecha_fin
            if hasattr(rep_db, "cerrada_por_id") and user and user.get("id"):
                rep_db.cerrada_por_id = int(user["id"])
            db.add(rep_db)
            db.flush()
            db.refresh(rep_db)
            return rep_db

    except OperationalError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Error temporal de base de datos")
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad")
    except DBAPIError:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")


@router.post(
    "/{reparacion_id}/reabrir",
    response_model=Reparacion,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def reabrir_reparacion(
    reparacion_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    rep = db.get(Reparacion, reparacion_id)
    if not rep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparación no encontrada")
    if rep.estado != "CERRADA":
        raise HTTPException(status.HTTP_409_CONFLICT, "La reparación no está cerrada")

    try:
        with db.begin():
            rep_db = db.exec(
                sa_select(Reparacion).where(Reparacion.id == rep.id).with_for_update()
            ).scalar_one()
            rep_db.estado = "ABIERTA"
            rep_db.fecha_fin = None
            if hasattr(rep_db, "cerrada_por_id"):
                rep_db.cerrada_por_id = None
            if hasattr(rep_db, "usuario_modificador_id") and user and user.get("id"):
                rep_db.usuario_modificador_id = int(user["id"])
            db.add(rep_db)
            db.flush()
            db.refresh(rep_db)
            return rep_db

    except OperationalError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Error temporal de base de datos")
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad")
    except DBAPIError:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")


@router.delete(
    "/{reparacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("ADMIN"))],
)
def eliminar_reparacion(
    reparacion_id: int,
    db: Session = Depends(get_db),
):
    rep = db.get(Reparacion, reparacion_id)
    if not rep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparación no encontrada")

    try:
        db.delete(rep)
        db.commit()
        return
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "No se puede eliminar la reparación (restricciones)")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")
