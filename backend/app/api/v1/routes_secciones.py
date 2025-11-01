# app/api/v1/routes_secciones.py

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy import func

from app.core.deps import get_db, current_user, require_role
from app.models.seccion import Seccion

router = APIRouter(prefix="/secciones", tags=["secciones"])

# ---------- Schemas ----------
class SeccionCreateIn(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150, description="Nombre único (case-insensitive)")

class SeccionUpdateIn(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=150)

# ---------- Helpers ----------
def _norm_name(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s2 = s.strip()
    return s2 or None

# ---------- Endpoints ----------
@router.post(
    "",
    response_model=Seccion,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN", check_db=False))],
)
def crear_seccion(
    payload: SeccionCreateIn,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    nombre = _norm_name(payload.nombre)
    if not nombre:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nombre requerido")

    obj = Seccion(nombre=nombre)
    try:
        db.add(obj)
        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        # choque por unique CITEXT
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Ya existe una sección con ese nombre")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno de base de datos")

    base_url = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base_url}/api/v1/secciones/{obj.id}"
    response.headers["Cache-Control"] = "no-store"
    return obj


@router.get(
    "",
    response_model=list[Seccion],
    dependencies=[Depends(require_role("OPERARIO", "MANTENIMIENTO", "ADMIN", check_db=False))],
)
def listar_secciones(
    response: Response,
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Filtro por nombre (icontains)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    ordenar: str = Query("nombre_asc", description="nombre_asc|nombre_desc|id_asc|id_desc"),
):
    stmt = select(Seccion)
    total_stmt = select(func.count()).select_from(Seccion)

    conds = []
    if q:
        qn = f"%{q.strip()}%"
        conds.append(func.lower(Seccion.nombre).like(func.lower(qn)))

    if conds:
        stmt = stmt.where(*conds)
        total_stmt = total_stmt.where(*conds)

    if ordenar == "nombre_desc":
        stmt = stmt.order_by(Seccion.nombre.desc(), Seccion.id.desc())
    elif ordenar == "id_asc":
        stmt = stmt.order_by(Seccion.id.asc())
    elif ordenar == "id_desc":
        stmt = stmt.order_by(Seccion.id.desc())
    else:  # nombre_asc
        stmt = stmt.order_by(Seccion.nombre.asc(), Seccion.id.asc())

    total = db.exec(total_stmt).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    stmt = stmt.limit(limit).offset(offset)
    return db.exec(stmt).all()


@router.get(
    "/{seccion_id}",
    response_model=Seccion,
    dependencies=[Depends(require_role("OPERARIO", "MANTENIMIENTO", "ADMIN", check_db=False))],
)
def obtener_seccion(seccion_id: int, db: Session = Depends(get_db)):
    obj = db.get(Seccion, seccion_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sección no encontrada")
    return obj


@router.patch(
    "/{seccion_id}",
    response_model=Seccion,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN", check_db=False))],
)
def actualizar_seccion(
    seccion_id: int,
    payload: SeccionUpdateIn,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    obj = db.get(Seccion, seccion_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sección no encontrada")

    changed = False
    if payload.nombre is not None:
        nombre = _norm_name(payload.nombre)
        if not nombre:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nombre inválido")
        obj.nombre = nombre
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
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Ya existe una sección con ese nombre")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno de base de datos")


@router.delete(
    "/{seccion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("ADMIN", check_db=False))],
)
def eliminar_seccion(seccion_id: int, db: Session = Depends(get_db)):
    obj = db.get(Seccion, seccion_id)
    if not obj:
        # idempotente
        return
    try:
        db.delete(obj)
        db.commit()
        return
    except IntegrityError:
        db.rollback()
        # Si hay ubicaciones/equipos enlazados y el FK no permite borrar, indicar conflicto
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: existen registros relacionados"
        )
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno de base de datos")
