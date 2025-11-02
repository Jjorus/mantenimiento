# backend/app/api/v1/routes_equipos.py
from typing import Optional, List, Dict, Any, Literal, get_args
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query, Body
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy import func

from app.core.deps import get_db, current_user, require_role
from app.models.equipo import Equipo
from app.models.seccion import Seccion
from app.models.ubicacion import Ubicacion

router = APIRouter(prefix="/equipos", tags=["equipos"])

# ---------- Constantes y Helpers ----------
EstadoEquipo = Literal["OPERATIVO", "MANTENIMIENTO", "BAJA", "CALIBRACION", "RESERVA"]
TIPOS_VALIDOS = {"Calibrador", "Multímetro", "Generador", "Osciloscopio", "Fuente", "Analizador", "Otro"}
# Mapa canónico: si llega "multimetro" -> "Multímetro", etc.
TIPOS_CANONICOS = {t.lower(): t for t in TIPOS_VALIDOS}

ALLOWED_ORDEN = {"id_asc", "id_desc", "identidad_asc", "identidad_desc", "tipo_asc", "tipo_desc"}

def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s2 = s.strip()
    return s2 if s2 else None

def _raise_422(errors: List[Dict[str, Any]]) -> None:
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

def _validar_tipo(tipo: str, errors: List[Dict[str, Any]]) -> None:
    """Valida que el tipo esté en la lista de tipos válidos."""
    if tipo not in TIPOS_VALIDOS:
        errors.append({
            "loc": ["body", "tipo"],
            "msg": f"Tipo inválido. Válidos: {', '.join(sorted(TIPOS_VALIDOS))}",
            "type": "value_error"
        })

# ---------- Schemas ----------
class EquipoCreateIn(BaseModel):
    identidad: Optional[str] = Field(None, min_length=1, max_length=100, examples=["EQ-0001"])
    numero_serie: Optional[str] = Field(None, max_length=150)
    tipo: str = Field(..., min_length=2, max_length=100, examples=["Calibrador"])
    estado: EstadoEquipo = Field("OPERATIVO", examples=["OPERATIVO"])
    seccion_id: Optional[int] = Field(None, gt=0)
    ubicacion_id: Optional[int] = Field(None, gt=0)
    nfc_tag: Optional[str] = Field(None, max_length=64)

class EquipoUpdateIn(BaseModel):
    identidad: Optional[str] = Field(None, min_length=1, max_length=100)
    numero_serie: Optional[str] = Field(None, max_length=150)
    tipo: Optional[str] = Field(None, min_length=2, max_length=100)
    estado: Optional[EstadoEquipo] = Field(None)
    seccion_id: Optional[int] = Field(None, gt=0)
    ubicacion_id: Optional[int] = Field(None, gt=0)
    nfc_tag: Optional[str] = Field(None, max_length=64)

class NFCAssignIn(BaseModel):
    nfc_tag: str = Field(..., min_length=1, max_length=64)

# ---------- Endpoints ----------
@router.post(
    "",
    response_model=Equipo,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("ADMIN", "MANTENIMIENTO"))],
)
def crear_equipo(
    payload: EquipoCreateIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Crea un equipo.
    - Normaliza identidad/nfc_tag en minúsculas (case-insensitive).
    - Verifica FKs de seccion/ubicacion y su coherencia.
    - Valida tipo y estado.
    - Maneja unicidad contra condiciones de carrera (409).
    """
    errors: List[Dict[str, Any]] = []

    identidad = _norm(payload.identidad)
    identidad = identidad.lower() if identidad else None
    nfc_tag = _norm(payload.nfc_tag)
    nfc_tag = nfc_tag.lower() if nfc_tag else None

    # Validaciones de negocio (con canonización opcional)
    tipo_req = (payload.tipo or "").strip()
    _validar_tipo(tipo_req, errors)
    tipo_final = TIPOS_CANONICOS.get(tipo_req.lower(), tipo_req)

    # FKs
    if payload.seccion_id is not None and not db.get(Seccion, payload.seccion_id):
        errors.append({"loc": ["body", "seccion_id"], "msg": "Sección inexistente", "type": "value_error.foreign_key"})
    if payload.ubicacion_id is not None and not db.get(Ubicacion, payload.ubicacion_id):
        errors.append({"loc": ["body", "ubicacion_id"], "msg": "Ubicación inexistente", "type": "value_error.foreign_key"})

    # Coherencia sección-ubicación (si llegan ambos)
    if payload.seccion_id is not None and payload.ubicacion_id is not None:
        u = db.get(Ubicacion, payload.ubicacion_id)
        if u and u.seccion_id and u.seccion_id != payload.seccion_id:
            errors.append({
                "loc": ["body", "ubicacion_id"],
                "msg": "La ubicación no pertenece a la sección indicada",
                "type": "value_error"
            })

    # Pre-chequeos de unicidad (UX) reforzados por índices únicos funcionales
    if identidad:
        if db.exec(select(Equipo).where(func.lower(Equipo.identidad) == identidad)).first():
            errors.append({"loc": ["body", "identidad"], "msg": "identidad ya existe", "type": "value_error.unique"})
    if nfc_tag:
        if db.exec(select(Equipo).where(func.lower(Equipo.nfc_tag) == nfc_tag)).first():
            errors.append({"loc": ["body", "nfc_tag"], "msg": "nfc_tag ya existe", "type": "value_error.unique"})

    if errors:
        _raise_422(errors)

    equipo = Equipo(
        identidad=identidad,
        numero_serie=_norm(payload.numero_serie),
        tipo=tipo_final,
        estado=payload.estado,
        seccion_id=payload.seccion_id,
        ubicacion_id=payload.ubicacion_id,
        nfc_tag=nfc_tag,
    )

    try:
        db.add(equipo)
        db.commit()
        db.refresh(equipo)
    except IntegrityError:
        db.rollback()
        # Carrera con índices únicos (LOWER(...))
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad (duplicado de identidad o nfc_tag)")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")

    base_url = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base_url}/api/v1/equipos/{equipo.id}"
    response.headers["Cache-Control"] = "no-store"
    return equipo


@router.get(
    "",
    response_model=list[Equipo],
    response_model_exclude_none=True,
    dependencies=[Depends(current_user)],
)
def listar_equipos(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Resultados por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento"),
    q: Optional[str] = Query(None, description="Búsqueda por identidad/serie/tipo (contiene)"),
    seccion_id: Optional[int] = Query(None, gt=0),
    ubicacion_id: Optional[int] = Query(None, gt=0),
    estado: Optional[EstadoEquipo] = Query(None),
    estados: Optional[str] = Query(None, description="Múltiples estados separados por coma"),
    ordenar: Optional[str] = Query("id_desc", description="id_asc|id_desc|identidad_asc|identidad_desc|tipo_asc|tipo_desc"),
    identidad_eq: Optional[str] = Query(None, description="Identidad exacta (case-insensitive)"),
    nfc_tag_eq: Optional[str] = Query(None, description="nfc_tag exacto (case-insensitive)"),
):
    """
    Lista equipos con filtros y paginación.
    Devuelve `X-Total-Count` con el total sin paginar.
    """
    if ordenar not in ALLOWED_ORDEN:
        _raise_422([{
            "loc": ["query", "ordenar"],
            "msg": f"Orden inválido. Válidos: {', '.join(sorted(ALLOWED_ORDEN))}",
            "type": "value_error"
        }])

    stmt = select(Equipo)
    count_stmt = select(func.count()).select_from(Equipo)

    # Filtros
    conds = []
    if q:
        like = f"%{q}%"
        conds.append((Equipo.identidad.ilike(like)) | (Equipo.numero_serie.ilike(like)) | (Equipo.tipo.ilike(like)))
    if identidad_eq:
        conds.append(func.lower(Equipo.identidad) == identidad_eq.strip().lower())
    if nfc_tag_eq:
        conds.append(func.lower(Equipo.nfc_tag) == nfc_tag_eq.strip().lower())
    if seccion_id:
        conds.append(Equipo.seccion_id == seccion_id)
    if ubicacion_id:
        conds.append(Equipo.ubicacion_id == ubicacion_id)
    if estado:
        conds.append(Equipo.estado == estado)
    if estados:
        estados_list = [e.strip() for e in estados.split(",") if e.strip()]
        estados_validos = [e for e in estados_list if e in get_args(EstadoEquipo)]
        if estados_validos:
            conds.append(Equipo.estado.in_(estados_validos))

    if conds:
        for c in conds:
            stmt = stmt.where(c)
            count_stmt = count_stmt.where(c)

    # Ordenamiento (estable y con nulos al final en identidad)
    if ordenar == "id_asc":
        stmt = stmt.order_by(Equipo.id.asc())
    elif ordenar == "identidad_asc":
        stmt = stmt.order_by(Equipo.identidad.asc().nulls_last(), Equipo.id.asc())
    elif ordenar == "identidad_desc":
        stmt = stmt.order_by(Equipo.identidad.desc().nulls_last(), Equipo.id.desc())
    elif ordenar == "tipo_asc":
        stmt = stmt.order_by(Equipo.tipo.asc(), Equipo.id.asc())
    elif ordenar == "tipo_desc":
        stmt = stmt.order_by(Equipo.tipo.desc(), Equipo.id.desc())
    else:  # id_desc por defecto
        stmt = stmt.order_by(Equipo.id.desc())

    total = db.exec(count_stmt).one()[0]
    response.headers["X-Total-Count"] = str(total)

    stmt = stmt.limit(limit).offset(offset)
    return db.exec(stmt).all()


@router.get(
    "/{equipo_id}",
    response_model=Equipo,
    response_model_exclude_none=True,
    dependencies=[Depends(current_user)],
)
def obtener_equipo(equipo_id: int, db: Session = Depends(get_db)):
    obj = db.get(Equipo, equipo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


@router.get(
    "/buscar/nfc/{nfc_tag}",
    response_model=Equipo,
    response_model_exclude_none=True,
    dependencies=[Depends(current_user)],
)
def buscar_equipo_por_nfc(nfc_tag: str, db: Session = Depends(get_db)):
    """
    Buscar equipo por NFC tag exacto (case-insensitive).
    """
    nfc_tag_clean = nfc_tag.strip().lower()
    equipo = db.exec(
        select(Equipo).where(func.lower(Equipo.nfc_tag) == nfc_tag_clean)
    ).first()

    if not equipo:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No se encontró ningún equipo con el NFC tag proporcionado"
        )

    return equipo


@router.get(
    "/buscar/identidad/{identidad}",
    response_model=Equipo,
    response_model_exclude_none=True,
    dependencies=[Depends(current_user)],
)
def buscar_equipo_por_identidad(identidad: str, db: Session = Depends(get_db)):
    """
    Buscar equipo por identidad exacta (case-insensitive).
    """
    ident = (identidad or "").strip().lower()
    equipo = db.exec(
        select(Equipo).where(func.lower(Equipo.identidad) == ident)
    ).first()
    if not equipo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe equipo con esa identidad")
    return equipo


@router.get(
    "/sin-ubicacion",
    response_model=list[Equipo],
    response_model_exclude_none=True,
    dependencies=[Depends(current_user)],
)
def listar_equipos_sin_ubicacion(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Listar equipos que no tienen ubicación asignada.
    """
    stmt = (
        select(Equipo)
        .where(Equipo.ubicacion_id.is_(None))
        .order_by(Equipo.id.desc())
        .limit(limit)
        .offset(offset)
    )

    count_stmt = select(func.count()).select_from(Equipo).where(Equipo.ubicacion_id.is_(None))
    total = db.exec(count_stmt).one()

    response.headers["X-Total-Count"] = str(total)
    return db.exec(stmt).all()


@router.patch(
    "/{equipo_id}",
    response_model=Equipo,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("ADMIN", "MANTENIMIENTO"))],
)
def actualizar_equipo(
    equipo_id: int,
    payload: EquipoUpdateIn,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Actualiza campos del equipo.
    - Normaliza identidad/nfc_tag en minúsculas.
    - Verifica FKs y tipos si se envían.
    - Coherencia sección-ubicación.
    - Maneja unicidad con IntegrityError (carreras).
    """
    obj = db.get(Equipo, equipo_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")

    errors: List[Dict[str, Any]] = []

    # Validaciones de negocio + canonización opcional del tipo
    if payload.tipo is not None:
        tipo_req = payload.tipo.strip()
        _validar_tipo(tipo_req, errors)
        tipo_final = TIPOS_CANONICOS.get(tipo_req.lower(), tipo_req)
    else:
        tipo_final = None

    if payload.estado is not None:
        if payload.estado not in get_args(EstadoEquipo):
            errors.append({
                "loc": ["body", "estado"],
                "msg": f"Estado inválido. Válidos: {', '.join(get_args(EstadoEquipo))}",
                "type": "value_error"
            })

    # FKs
    if payload.seccion_id is not None and not db.get(Seccion, payload.seccion_id):
        errors.append({"loc": ["body", "seccion_id"], "msg": "Sección inexistente", "type": "value_error.foreign_key"})
    if payload.ubicacion_id is not None and not db.get(Ubicacion, payload.ubicacion_id):
        errors.append({"loc": ["body", "ubicacion_id"], "msg": "Ubicación inexistente", "type": "value_error.foreign_key"})

    # Coherencia sección-ubicación (considera valores nuevos o actuales)
    new_seccion_id = payload.seccion_id if payload.seccion_id is not None else obj.seccion_id
    new_ubic_id    = payload.ubicacion_id if payload.ubicacion_id is not None else obj.ubicacion_id
    if new_seccion_id is not None and new_ubic_id is not None:
        u = db.get(Ubicacion, new_ubic_id)
        if u and u.seccion_id and u.seccion_id != new_seccion_id:
            errors.append({
                "loc": ["body", "ubicacion_id"],
                "msg": "La ubicación no pertenece a la sección indicada",
                "type": "value_error"
            })

    # Pre-validaciones de unicidad (case-insensitive)
    identidad = _norm(payload.identidad) if payload.identidad is not None else None
    identidad = identidad.lower() if identidad else None
    nfc_tag = _norm(payload.nfc_tag) if payload.nfc_tag is not None else None
    nfc_tag = nfc_tag.lower() if nfc_tag else None

    if identidad is not None and identidad != (obj.identidad.lower() if obj.identidad else None):
        if db.exec(select(Equipo).where(func.lower(Equipo.identidad) == identidad)).first():
            errors.append({"loc": ["body", "identidad"], "msg": "identidad ya existe", "type": "value_error.unique"})

    if nfc_tag is not None and nfc_tag != (obj.nfc_tag.lower() if obj.nfc_tag else None):
        if db.exec(select(Equipo).where(func.lower(Equipo.nfc_tag) == nfc_tag)).first():
            errors.append({"loc": ["body", "nfc_tag"], "msg": "nfc_tag ya existe", "type": "value_error.unique"})

    if errors:
        _raise_422(errors)

    # Asignaciones condicionadas
    if payload.identidad is not None:
        obj.identidad = identidad
    if payload.numero_serie is not None:
        obj.numero_serie = _norm(payload.numero_serie)
    if payload.tipo is not None:
        obj.tipo = tipo_final
    if payload.estado is not None:
        obj.estado = payload.estado
    if payload.seccion_id is not None:
        obj.seccion_id = payload.seccion_id
    if payload.ubicacion_id is not None:
        obj.ubicacion_id = payload.ubicacion_id
    if payload.nfc_tag is not None:
        obj.nfc_tag = nfc_tag

    try:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad (duplicado de identidad o nfc_tag)")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")


@router.delete(
    "/{equipo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("ADMIN"))],
)
def eliminar_equipo(equipo_id: int, db: Session = Depends(get_db)):
    """
    Elimina un equipo (solo ADMIN).
    Considera restricciones de FK en movimientos/incidencias/reparaciones.
    """
    obj = db.get(Equipo, equipo_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")

    try:
        db.delete(obj)
        db.commit()
        return  # 204 No Content
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede eliminar: equipo tiene movimientos, incidencias o reparaciones asociadas"
        )


@router.get(
    "/estadisticas/resumen",
    response_model_exclude_none=True,
    dependencies=[Depends(current_user)],
)
def resumen_estadisticas(db: Session = Depends(get_db)):
    """
    Resumen estadístico de equipos.
    """
    total = db.exec(select(func.count(Equipo.id))).one()

    # Evitar claves None en el dict final
    por_estado_rows = db.exec(
        select(Equipo.estado, func.count(Equipo.id)).group_by(Equipo.estado)
    ).all()
    por_estado = {k: v for k, v in por_estado_rows if k is not None}

    por_tipo_rows = db.exec(
        select(Equipo.tipo, func.count(Equipo.id))
        .group_by(Equipo.tipo)
        .order_by(func.count(Equipo.id).desc())
        .limit(10)
    ).all()
    por_tipo = {k: v for k, v in por_tipo_rows if k is not None}

    sin_ubicacion = db.exec(
        select(func.count(Equipo.id)).where(Equipo.ubicacion_id.is_(None))
    ).one()

    return {
        "total_equipos": total,
        "por_estado": por_estado,
        "tipos_mas_comunes": por_tipo,
        "sin_ubicacion": sin_ubicacion,
        "con_ubicacion": total - sin_ubicacion,
    }


@router.post(
    "/{equipo_id}/nfc/assign",
    response_model=Equipo,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def asignar_nfc(
    equipo_id: int,
    payload: NFCAssignIn,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    tag = (payload.nfc_tag or "").strip().lower()
    if not tag:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "nfc_tag vacío")

    eq = db.get(Equipo, equipo_id)
    if not eq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")

    # ¿tag ya en uso?
    conflict = db.exec(
        select(Equipo).where(func.lower(Equipo.nfc_tag) == tag, Equipo.id != equipo_id)
    ).first()
    if conflict:
        raise HTTPException(status.HTTP_409_CONFLICT, "nfc_tag ya asignado a otro equipo")

    eq.nfc_tag = tag
    try:
        db.add(eq)
        db.commit()
        db.refresh(eq)
        return eq
    except IntegrityError:
        db.rollback()
        # por si el UNIQUE funcional pilla una carrera
        raise HTTPException(status.HTTP_409_CONFLICT, "nfc_tag ya asignado")


@router.delete(
    "/{equipo_id}/nfc",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def desasignar_nfc(
    equipo_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    eq = db.get(Equipo, equipo_id)
    if not eq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")
    if not eq.nfc_tag:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    eq.nfc_tag = None
    db.add(eq)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
