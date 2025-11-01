# backend/app/api/v1/routes_movimientos.py

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import select as sa_select, func
from sqlalchemy.exc import OperationalError, DBAPIError, IntegrityError

from app.core.deps import get_db, current_user, require_role
from app.models.equipo import Equipo
from app.models.ubicacion import Ubicacion
from app.models.movimiento import Movimiento

# >>> NUEVO: helpers de seguridad (NFC / RL / Idempotencia / Debounce)
from app.core.security import (
    assert_idempotent,
    assert_debounce,
    check_rate_limit_nfc,
)

router = APIRouter(prefix="/movimientos", tags=["movimientos"])

# ---------- Helpers ----------
def _norm_str(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s2 = s.strip()
    return s2 or None

def _raise_422(errors: List[Dict[str, Any]]) -> None:
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

ALLOWED_ORDEN = {"fecha_desc", "fecha_asc", "id_desc", "id_asc"}

# ---------- Schemas ----------
class MovimientoBase(BaseModel):
    equipo_id: int = Field(..., gt=0, examples=[1])
    hacia_ubicacion_id: int = Field(..., gt=0, examples=[3])
    comentario: Optional[str] = Field(None, max_length=500, examples=["Entrega a operario"])

class RetirarIn(MovimientoBase):
    """Payload para retirar un equipo de su ubicación actual"""

class DevolverIn(MovimientoBase):
    """Payload para devolver un equipo a una ubicación específica"""

class MovimientoPatchIn(BaseModel):
    comentario: Optional[str] = Field(None, max_length=500)

# ---------- Core ----------
def _mover_equipo(
    db: Session,
    equipo_id: int,
    nueva_ubicacion_id: int,
    comentario: Optional[str] = None,
    actor_id: Optional[int] = None,
) -> Movimiento:
    try:
        with db.begin():
            # Bloqueo pesimista para evitar carreras
            eq = db.exec(
                sa_select(Equipo).where(Equipo.id == equipo_id).with_for_update()
            ).scalar_one_or_none()
            if not eq:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

            dest = db.get(Ubicacion, nueva_ubicacion_id)
            if not dest:
                # 422 al estilo Pydantic
                _raise_422([{
                    "loc": ["body", "hacia_ubicacion_id"],
                    "msg": "Ubicación destino inexistente",
                    "type": "value_error.foreign_key",
                }])

            # Reglas de negocio de movibilidad
            if hasattr(eq, "puede_moverse"):
                if not eq.puede_moverse:
                    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El equipo no puede moverse en su estado actual")
            else:
                if getattr(eq, "estado", None) in {"BAJA"}:
                    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El equipo no puede moverse en su estado actual")

            if eq.ubicacion_id == nueva_ubicacion_id:
                # 409: ya está en el destino
                raise HTTPException(status.HTTP_409_CONFLICT, detail="El equipo ya se encuentra en esta ubicación")

            mov = Movimiento(
                equipo_id=eq.id,
                desde_ubicacion_id=eq.ubicacion_id,
                hacia_ubicacion_id=dest.id,
                comentario=_norm_str(comentario),
            )
            if hasattr(Movimiento, "usuario_id") and actor_id is not None:
                mov.usuario_id = actor_id

            eq.ubicacion_id = dest.id

            db.add_all([mov, eq])
            db.flush()
            db.refresh(mov)
            return mov

    except OperationalError:
        # deadlocks/timeouts → 503 temporal
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos. Intente nuevamente."
        )
    except IntegrityError:
        # conflictos de integridad (FK, etc.)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Conflicto de integridad (revise FK/estado)."
        )
    except DBAPIError:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno de base de datos"
        )

# ---------- Endpoints de acción ----------
@router.post(
    "/retirar",
    response_model=Movimiento,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("OPERARIO", "MANTENIMIENTO", "ADMIN"))],
)
def retirar(
    payload: RetirarIn,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Retirar equipo de su ubicación actual y moverlo a una nueva ubicación.
    Típicamente usado cuando un técnico se lleva el equipo.
    """
    mov = _mover_equipo(db, payload.equipo_id, payload.hacia_ubicacion_id, payload.comentario, int(user["id"]))
    base_url = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base_url}/api/v1/movimientos/{mov.id}"
    response.headers["Cache-Control"] = "no-store"
    return mov

@router.post(
    "/devolver",
    response_model=Movimiento,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("OPERARIO", "MANTENIMIENTO", "ADMIN"))],
)
def devolver(
    payload: DevolverIn,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Devolver equipo a una ubicación específica (almacén, zona, etc.).
    Típicamente usado cuando un técnico regresa el equipo.
    """
    mov = _mover_equipo(db, payload.equipo_id, payload.hacia_ubicacion_id, payload.comentario, int(user["id"]))
    base_url = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base_url}/api/v1/movimientos/{mov.id}"
    response.headers["Cache-Control"] = "no-store"
    return mov

# ---------- Listados & lectura ----------
@router.get(
    "",
    response_model=list[Movimiento],
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def listar_movimientos(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados (1-200)"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    desde: datetime | None = Query(None, description="Filtrar desde esta fecha (ISO-8601, UTC)"),
    hasta: datetime | None = Query(None, description="Filtrar hasta esta fecha (ISO-8601, UTC)"),
    equipo_id: int | None = Query(None, gt=0, description="Filtrar por ID de equipo"),
    desde_ubicacion_id: int | None = Query(None, gt=0, description="Filtrar por ubicación de origen"),
    hacia_ubicacion_id: int | None = Query(None, gt=0, description="Filtrar por ubicación de destino"),
    ordenar: str = Query("fecha_desc", description="fecha_desc|fecha_asc|id_desc|id_asc"),
):
    """
    Listar movimientos con filtros, orden y paginación.
    Devuelve cabecera `X-Total-Count` con el total sin paginar.
    """
    if ordenar not in ALLOWED_ORDEN:
        _raise_422([{
            "loc": ["query", "ordenar"],
            "msg": f"Orden inválido. Válidos: {', '.join(sorted(ALLOWED_ORDEN))}",
            "type": "value_error"
        }])

    if desde and hasta and desde > hasta:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Rango de fechas inválido (desde > hasta)")

    total_stmt = select(func.count()).select_from(Movimiento)
    data_stmt = select(Movimiento)

    conds = []
    if equipo_id:
        conds.append(Movimiento.equipo_id == equipo_id)
    if desde_ubicacion_id:
        conds.append(Movimiento.desde_ubicacion_id == desde_ubicacion_id)
    if hacia_ubicacion_id:
        conds.append(Movimiento.hacia_ubicacion_id == hacia_ubicacion_id)
    if desde:
        conds.append(Movimiento.fecha >= desde)
    if hasta:
        conds.append(Movimiento.fecha <= hasta)

    if conds:
        total_stmt = total_stmt.where(*conds)
        data_stmt = data_stmt.where(*conds)

    # Orden
    if ordenar == "fecha_asc":
        data_stmt = data_stmt.order_by(Movimiento.fecha.asc(), Movimiento.id.asc())
    elif ordenar == "id_asc":
        data_stmt = data_stmt.order_by(Movimiento.id.asc())
    elif ordenar == "id_desc":
        data_stmt = data_stmt.order_by(Movimiento.id.desc())
    else:  # fecha_desc
        data_stmt = data_stmt.order_by(Movimiento.fecha.desc(), Movimiento.id.desc())

    total = db.exec(total_stmt).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    data_stmt = data_stmt.limit(limit).offset(offset)
    return db.exec(data_stmt).all()

@router.get(
    "/equipo/{equipo_id}",
    response_model=list[Movimiento],
    response_model_exclude_none=True,
    dependencies=[Depends(current_user)],
)
def historial_equipo(
    equipo_id: int,
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados (1-200)"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
):
    """
    Historial de movimientos de un equipo (autenticado).
    Devuelve cabecera `X-Total-Count` del total del historial.
    """
    eq = db.get(Equipo, equipo_id)
    if not eq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

    total = db.exec(
        select(func.count()).select_from(Movimiento).where(Movimiento.equipo_id == equipo_id)
    ).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    stmt = (
        select(Movimiento)
        .where(Movimiento.equipo_id == equipo_id)
        .order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.exec(stmt).all()

@router.get(
    "/{movimiento_id}",
    response_model=Movimiento,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def obtener_movimiento(movimiento_id: int, db: Session = Depends(get_db)):
    """
    Obtener un movimiento por ID (roles: mantenimiento/admin).
    """
    mov = db.get(Movimiento, movimiento_id)
    if not mov:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Movimiento no encontrado")
    return mov

@router.patch(
    "/{movimiento_id}",
    response_model=Movimiento,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def actualizar_movimiento(
    movimiento_id: int,
    payload: MovimientoPatchIn,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Actualiza campos permitidos del movimiento (comentario).
    No se cambia equipo ni ubicaciones en histórico (trazabilidad).
    """
    obj = db.get(Movimiento, movimiento_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Movimiento no encontrado")

    changed = False
    if payload.comentario is not None:
        obj.comentario = _norm_str(payload.comentario)
        changed = True

    if not changed:
        return obj

    try:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Conflicto de integridad en la base de datos")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno de base de datos")


# ---------- NFC ----------
class MovimientoNFCIn(BaseModel):
    nfc_tag: str = Field(..., min_length=1, max_length=64)
    hacia_ubicacion_id: int = Field(..., gt=0)
    comentario: Optional[str] = Field(None, max_length=500)

def _equipo_por_nfc_or_404(db: Session, nfc_tag: str) -> Equipo:
    tag = (nfc_tag or "").strip().lower()
    eq = db.exec(select(Equipo).where(func.lower(Equipo.nfc_tag) == tag)).first()
    if not eq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe equipo con ese nfc_tag")
    return eq

@router.post(
    "/retirar/nfc",
    response_model=Movimiento,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("OPERARIO", "MANTENIMIENTO", "ADMIN"))],
)
def retirar_por_nfc(
    payload: MovimientoNFCIn,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    # --- Seguridad NFC: idempotencia + debounce + rate limit ---
    assert_idempotent(request, ttl_sec=30)
    assert_debounce(f"nfc:{user['id']}:{payload.nfc_tag}:retirar", ttl_sec=3)
    check_rate_limit_nfc(str(user["id"]), payload.nfc_tag, limit=5, window_sec=10)

    eq = _equipo_por_nfc_or_404(db, payload.nfc_tag)
    mov = _mover_equipo(
        db, eq.id, payload.hacia_ubicacion_id, payload.comentario, int(user["id"])
    )
    base_url = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base_url}/api/v1/movimientos/{mov.id}"
    response.headers["Cache-Control"] = "no-store"
    return mov

@router.post(
    "/devolver/nfc",
    response_model=Movimiento,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("OPERARIO", "MANTENIMIENTO", "ADMIN"))],
)
def devolver_por_nfc(
    payload: MovimientoNFCIn,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    # --- Seguridad NFC: idempotencia + debounce + rate limit ---
    assert_idempotent(request, ttl_sec=30)
    assert_debounce(f"nfc:{user['id']}:{payload.nfc_tag}:devolver", ttl_sec=3)
    check_rate_limit_nfc(str(user["id"]), payload.nfc_tag, limit=5, window_sec=10)

    eq = _equipo_por_nfc_or_404(db, payload.nfc_tag)
    mov = _mover_equipo(
        db, eq.id, payload.hacia_ubicacion_id, payload.comentario, int(user["id"])
    )
    base_url = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base_url}/api/v1/movimientos/{mov.id}"
    response.headers["Cache-Control"] = "no-store"
    return mov
