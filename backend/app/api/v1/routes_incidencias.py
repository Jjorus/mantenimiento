# backend/app/api/v1/routes_incidencias.py
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func, select as sa_select
from sqlalchemy.exc import IntegrityError, DBAPIError, OperationalError

from app.core.deps import get_db, current_user, require_role
from app.models.incidencia import Incidencia
from app.models.equipo import Equipo

router = APIRouter(prefix="/incidencias", tags=["incidencias"])

Estado = Literal["ABIERTA", "EN_PROGRESO", "CERRADA"]
ALLOWED_ORDEN = {"fecha_desc", "fecha_asc", "id_desc", "id_asc"}

# ---------- Helpers ----------
def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s2 = s.strip()
    return s2 if s2 else None

def _raise_422(errors: List[Dict[str, Any]]) -> None:
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

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
    Crear una incidencia (por defecto: ABIERTA).
    Registra usuario creador si el modelo lo soporta.
    """
    # FK equipo con error estilo 422
    eq = db.get(Equipo, payload.equipo_id)
    if not eq:
        _raise_422([{"loc": ["body", "equipo_id"], "msg": "Equipo inexistente", "type": "value_error.foreign_key"}])

    inc = Incidencia(
        equipo_id=eq.id,
        titulo=_norm(payload.titulo),
        descripcion=_norm(payload.descripcion),
    )
    if hasattr(Incidencia, "usuario_id") and user and user.get("id"):
        setattr(inc, "usuario_id", int(user["id"]))

    try:
        db.add(inc)
        db.commit()
        db.refresh(inc)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad en la base de datos")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")

    base_url = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base_url}/api/v1/incidencias/{inc.id}"
    response.headers["Cache-Control"] = "no-store"
    return inc


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
    q: Optional[str] = Query(None, description="Buscar en título/descripcion (ILIKE)"),
    estado: Optional[Estado] = Query(None, description="Filtrar por estado"),
    estados: Optional[str] = Query(None, description="Múltiples estados separados por coma"),
    equipo_id: Optional[int] = Query(None, gt=0, description="Filtrar por ID de equipo"),
    desde: datetime | None = Query(None, description="Desde fecha (ISO-8601, UTC)"),
    hasta: datetime | None = Query(None, description="Hasta fecha (ISO-8601, UTC)"),
    ordenar: str = Query("fecha_desc", description="fecha_desc|fecha_asc|id_desc|id_asc"),
):
    """
    Listar incidencias con filtros/orden/paginación.
    Devuelve cabecera `X-Total-Count` con el total sin paginar.
    """
    if ordenar not in ALLOWED_ORDEN:
        _raise_422([{
            "loc": ["query", "ordenar"],
            "msg": f"Orden inválido. Válidos: {', '.join(sorted(ALLOWED_ORDEN))}",
            "type": "value_error"
        }])
    if desde and hasta and desde > hasta:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rango de fechas inválido (desde > hasta)")

    total_stmt = select(func.count()).select_from(Incidencia)
    data_stmt = select(Incidencia)

    conds = []
    if q:
        like = f"%{q.strip()}%"
        conds.append((Incidencia.titulo.ilike(like)) | (Incidencia.descripcion.ilike(like)))
    if estado:
        conds.append(Incidencia.estado == estado)
    if estados:
        lista = [e.strip().upper() for e in estados.split(",") if e.strip()]
        validos = [e for e in lista if e in Estado.__args__]
        if validos:
            conds.append(Incidencia.estado.in_(validos))
    if equipo_id:
        conds.append(Incidencia.equipo_id == equipo_id)
    if desde:
        conds.append(Incidencia.fecha >= desde)
    if hasta:
        conds.append(Incidencia.fecha <= hasta)

    if conds:
        total_stmt = total_stmt.where(*conds)
        data_stmt = data_stmt.where(*conds)

    # Orden
    if ordenar == "fecha_asc":
        data_stmt = data_stmt.order_by(Incidencia.fecha.asc(), Incidencia.id.asc())
    elif ordenar == "id_asc":
        data_stmt = data_stmt.order_by(Incidencia.id.asc())
    elif ordenar == "id_desc":
        data_stmt = data_stmt.order_by(Incidencia.id.desc())
    else:  # fecha_desc
        data_stmt = data_stmt.order_by(Incidencia.fecha.desc(), Incidencia.id.desc())

    total = db.exec(total_stmt).one()
    response.headers["X-Total-Count"] = str(total)

    data_stmt = data_stmt.limit(limit).offset(offset)
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
    Actualiza una incidencia (solo MANTENIMIENTO/ADMIN).
    Usa reglas de dominio para transiciones de estado; resto de campos se editan libremente.
    Bloqueo pesimista y transacción segura para coherencia.
    """
    obj = db.get(Incidencia, incidencia_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")

    # Elegir contexto transaccional (savepoint si ya hay tx abierta)
    tx_ctx = db.begin_nested() if db.in_transaction() else db.begin()

    try:
        with tx_ctx:
            # Releer con FOR UPDATE para evitar carreras
            inc_db = db.exec(
                sa_select(Incidencia).where(Incidencia.id == obj.id).with_for_update()
            ).scalar_one()

            changed = False

            if payload.titulo is not None:
                titulo = _norm(payload.titulo)
                if not titulo:
                    _raise_422([{"loc": ["body", "titulo"], "msg": "El título no puede estar vacío", "type": "value_error"}])
                inc_db.titulo = titulo
                changed = True

            if payload.descripcion is not None:
                inc_db.descripcion = _norm(payload.descripcion)
                changed = True

            if payload.estado is not None:
                estado_actual = inc_db.estado
                estado_nuevo = payload.estado

                if estado_nuevo == "CERRADA" and estado_actual != "CERRADA":
                    inc_db.cerrar(int(user["id"]))
                    changed = True
                elif estado_nuevo in {"ABIERTA", "EN_PROGRESO"} and estado_actual == "CERRADA":
                    inc_db.reabrir(int(user["id"]))
                    changed = True
                elif estado_nuevo != estado_actual:
                    inc_db.estado = estado_nuevo
                    if hasattr(Incidencia, "usuario_modificador_id") and user and user.get("id"):
                        inc_db.usuario_modificador_id = int(user["id"])
                    changed = True

            if not changed:
                return inc_db

            db.add(inc_db)
            db.flush()
            db.refresh(inc_db)
            return inc_db

    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except OperationalError:
        db.rollback()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Error temporal de base de datos")
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
    Usa transacción segura + FOR UPDATE para evitar condiciones de carrera.
    """
    obj = db.get(Incidencia, incidencia_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")

    tx_ctx = db.begin_nested() if db.in_transaction() else db.begin()

    try:
        with tx_ctx:
            inc_db = db.exec(
                sa_select(Incidencia).where(Incidencia.id == obj.id).with_for_update()
            ).scalar_one()

            # Idempotente: si ya está cerrada devolvemos tal cual
            if inc_db.estado != "CERRADA":
                inc_db.cerrar(int(user["id"]))

            db.add(inc_db)
            db.flush()
            db.refresh(inc_db)

        base_url = str(request.base_url).rstrip("/")
        response.headers["Location"] = f"{base_url}/api/v1/incidencias/{inc_db.id}"
        response.headers["Cache-Control"] = "no-store"
        return inc_db

    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except OperationalError:
        db.rollback()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Error temporal de base de datos")
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
    Usa transacción segura + FOR UPDATE para evitar condiciones de carrera.
    """
    obj = db.get(Incidencia, incidencia_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")

    tx_ctx = db.begin_nested() if db.in_transaction() else db.begin()

    try:
        with tx_ctx:
            inc_db = db.exec(
                sa_select(Incidencia).where(Incidencia.id == obj.id).with_for_update()
            ).scalar_one()

            # Si no está cerrada, 409; si lo prefieres, puedes hacerlo idempotente
            if inc_db.estado != "CERRADA":
                raise HTTPException(status.HTTP_409_CONFLICT, "La incidencia no está cerrada")

            inc_db.reabrir(int(user["id"]))
            db.add(inc_db)
            db.flush()
            db.refresh(inc_db)

        base_url = str(request.base_url).rstrip("/")
        response.headers["Location"] = f"{base_url}/api/v1/incidencias/{inc_db.id}"
        response.headers["Cache-Control"] = "no-store"
        return inc_db

    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except OperationalError:
        db.rollback()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Error temporal de base de datos")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad en la base de datos")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")
