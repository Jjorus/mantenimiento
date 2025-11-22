# backend/app/api/v1/routes_ubicaciones.py
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy import func

from app.core.deps import get_db, current_user, require_role
from app.models.ubicacion import Ubicacion
from app.models.seccion import Seccion

router = APIRouter(prefix="/ubicaciones", tags=["ubicaciones"])

# ---------- Helpers ----------
ALLOWED_ORDEN = {"id_desc", "id_asc", "nombre_asc", "nombre_desc", "creado_desc", "creado_asc"}

def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s2 = s.strip()
    return s2 or None

def _raise_422(errors: List[Dict[str, Any]]) -> None:
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

# ---------- Schemas ----------
class UbicacionCreateIn(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150, examples=["Almacén Central"])
    seccion_id: Optional[int] = Field(None, gt=0)

class UbicacionUpdateIn(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=150)
    seccion_id: Optional[int] = Field(None, gt=0)

# ---------- Endpoints ----------
@router.post(
    "",
    response_model=Ubicacion,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def crear_ubicacion(
    payload: UbicacionCreateIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Crea una ubicación.
    - Normaliza `nombre`.
    - Verifica FK de `seccion_id` si se envía.
    - Maneja unicidad de `nombre`.
    """
    errors: List[Dict[str, Any]] = []

    nombre = _norm(payload.nombre)
    if not nombre:
        errors.append({"loc": ["body", "nombre"], "msg": "nombre no puede estar vacío", "type": "value_error"})
    if payload.seccion_id is not None and not db.get(Seccion, payload.seccion_id):
        errors.append({"loc": ["body", "seccion_id"], "msg": "Sección inexistente", "type": "value_error.foreign_key"})

    # Pre-chequeo de unicidad (UX). La BD lo refuerza con UNIQUE.
    if nombre:
        existe = db.exec(select(Ubicacion).where(Ubicacion.nombre == nombre)).first()
        if existe:
            errors.append({"loc": ["body", "nombre"], "msg": "nombre ya existe", "type": "value_error.unique"})

    if errors:
        _raise_422(errors)

    obj = Ubicacion(nombre=nombre, seccion_id=payload.seccion_id)

    try:
        db.add(obj)
        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Conflicto de integridad (nombre duplicado o FK inválida)")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno de base de datos")

    base_url = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base_url}/api/v1/ubicaciones/{obj.id}"
    response.headers["Cache-Control"] = "no-store"
    return obj


@router.get(
    "",
    response_model=list[Ubicacion],
    response_model_exclude_none=True,
    dependencies=[Depends(current_user)],
)
def listar_ubicaciones(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Resultados por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento"),
    q: Optional[str] = Query(None, description="Búsqueda por nombre (contiene)"),
    seccion_id: Optional[int] = Query(None, gt=0),
    ordenar: str = Query("id_desc", description="id_desc|id_asc|nombre_asc|nombre_desc|creado_desc|creado_asc"),
):
    """
    Lista ubicaciones con filtros y paginación.
    Devuelve `X-Total-Count` con el total sin paginar.
    Requiere autenticación.
    """
    if ordenar not in ALLOWED_ORDEN:
        _raise_422([{
            "loc": ["query", "ordenar"],
            "msg": f"Orden inválido. Válidos: {', '.join(sorted(ALLOWED_ORDEN))}",
            "type": "value_error"
        }])

    stmt = select(Ubicacion)
    count_stmt = select(func.count()).select_from(Ubicacion)

    conds = []
    if q:
        like = f"%{q.strip()}%"
        conds.append(Ubicacion.nombre.ilike(like))
    if seccion_id:
        conds.append(Ubicacion.seccion_id == seccion_id)

    if conds:
        for c in conds:
            stmt = stmt.where(c)
            count_stmt = count_stmt.where(c)

    # Orden
    if ordenar == "id_asc":
        stmt = stmt.order_by(Ubicacion.id.asc())
    elif ordenar == "nombre_asc":
        stmt = stmt.order_by(Ubicacion.nombre.asc())
    elif ordenar == "nombre_desc":
        stmt = stmt.order_by(Ubicacion.nombre.desc())
    elif ordenar == "creado_asc":
        # si el modelo tiene creado_en; si no, cae a id_asc
        if hasattr(Ubicacion, "creado_en"):
            stmt = stmt.order_by(Ubicacion.creado_en.asc(), Ubicacion.id.asc())
        else:
            stmt = stmt.order_by(Ubicacion.id.asc())
    elif ordenar == "creado_desc":
        if hasattr(Ubicacion, "creado_en"):
            stmt = stmt.order_by(Ubicacion.creado_en.desc(), Ubicacion.id.desc())
        else:
            stmt = stmt.order_by(Ubicacion.id.desc())
    else:  # id_desc
        stmt = stmt.order_by(Ubicacion.id.desc())

    total = db.exec(count_stmt).one()
    response.headers["X-Total-Count"] = str(total)

    stmt = stmt.limit(limit).offset(offset)
    return db.exec(stmt).all()


@router.get(
    "/{ubicacion_id}",
    response_model=Ubicacion,
    response_model_exclude_none=True,
    dependencies=[Depends(current_user)],
)
def obtener_ubicacion(ubicacion_id: int, db: Session = Depends(get_db)):
    obj = db.get(Ubicacion, ubicacion_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada")
    return obj


@router.patch(
    "/{ubicacion_id}",
    response_model=Ubicacion,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def actualizar_ubicacion(
    ubicacion_id: int,
    payload: UbicacionUpdateIn,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Actualiza nombre y/o seccion_id.
    Maneja unicidad de nombre y FK de sección.
    """
    obj = db.get(Ubicacion, ubicacion_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada")

    errors: List[Dict[str, Any]] = []

    # Validaciones previas
    nombre = _norm(payload.nombre) if payload.nombre is not None else None
    if nombre is not None and nombre != obj.nombre:
        existe = db.exec(select(Ubicacion).where(Ubicacion.nombre == nombre)).first()
        if existe:
            errors.append({"loc": ["body", "nombre"], "msg": "nombre ya existe", "type": "value_error.unique"})

    if payload.seccion_id is not None and not db.get(Seccion, payload.seccion_id):
        errors.append({"loc": ["body", "seccion_id"], "msg": "Sección inexistente", "type": "value_error.foreign_key"})

    if errors:
        _raise_422(errors)

    # Asignaciones condicionadas
    changed = False
    if payload.nombre is not None:
        obj.nombre = nombre
        changed = True
    if payload.seccion_id is not None:
        obj.seccion_id = payload.seccion_id
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
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Conflicto de integridad (nombre duplicado o FK inválida)")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno de base de datos")


@router.delete(
    "/{ubicacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("ADMIN"))],
)
def eliminar_ubicacion(ubicacion_id: int, db: Session = Depends(get_db)):
    """
    Elimina una ubicación (solo ADMIN).
    Si hay equipos apuntando a la ubicación y la FK está como SET NULL,
    la eliminación será válida; si hubiese ON RESTRICT, lanzará IntegrityError.
    """
    obj = db.get(Ubicacion, ubicacion_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada")

    try:
        db.delete(obj)
        db.commit()
        return  # 204
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="No se puede eliminar la ubicación por restricciones de integridad"
        )
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno de base de datos")


@router.get(
    "/estadisticas/resumen",
    dependencies=[Depends(current_user)],
)
def resumen_ubicaciones(db: Session = Depends(get_db)):
    """
    Resumen rápido: total ubicaciones y por sección (si existe).
    """
    total = db.exec(select(func.count(Ubicacion.id))).one()

    if hasattr(Ubicacion, "seccion_id"):
        por_seccion_rows = db.exec(
            select(Ubicacion.seccion_id, func.count(Ubicacion.id))
            .group_by(Ubicacion.seccion_id)
            .order_by(func.count(Ubicacion.id).desc())
        ).all()
        # Limpia claves None
        por_seccion = {str(k): v for k, v in por_seccion_rows if k is not None}
    else:
        por_seccion = {}

    return {
        "total_ubicaciones": total,
        "por_seccion": por_seccion,
    }
