# backend/app/api/v1/routes_equipos.py
from typing import Optional, List, Dict, Any, Literal, get_args
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy import func

from app.core.deps import get_db, current_user, require_role
from app.core.file_manager import FileManager
from app.models.equipo import Equipo
from app.models.seccion import Seccion
from app.models.ubicacion import Ubicacion
from app.models.equipo_adjunto import EquipoAdjunto

router = APIRouter(prefix="/equipos", tags=["equipos"])

# ---------- Constantes y Helpers ----------
EstadoEquipo = Literal["OPERATIVO", "MANTENIMIENTO", "BAJA", "CALIBRACION", "RESERVA"]
TIPOS_VALIDOS = {
    "Masas",
    "Fuerza",
    "Dimensional",
    "3D",
    "Par",
    "Verificación Dimensional",
    "Temperatura",
    "Electricidad",
    "Químico",
    "Limpieza",
    "Acelerómetros",
    "Acústica",
    "Caudal",
    "Presión",
    "Densidad y Volumen",
    "Óptica y radiometría",
    "Ultrasonidos",
    "Calibrador",
    "Multímetro",
    "Generador",
    "Osciloscopio",
    "Fuente",
    "Analizador",
    "Otro",
}
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
    notas: Optional[str] = Field(None, description="Comentarios o notas del equipo") # <--- NUEVO
    seccion_id: Optional[int] = Field(None, gt=0)
    ubicacion_id: Optional[int] = Field(None, gt=0)
    nfc_tag: Optional[str] = Field(None, max_length=64)

class EquipoUpdateIn(BaseModel):
    identidad: Optional[str] = Field(None, min_length=1, max_length=100)
    numero_serie: Optional[str] = Field(None, max_length=150)
    tipo: Optional[str] = Field(None, min_length=2, max_length=100)
    estado: Optional[EstadoEquipo] = Field(None)
    notas: Optional[str] = Field(None) # <--- NUEVO
    seccion_id: Optional[int] = Field(None, gt=0)
    ubicacion_id: Optional[int] = Field(None, gt=0)
    nfc_tag: Optional[str] = Field(None, max_length=64)

class NFCAssignIn(BaseModel):
    nfc_tag: str = Field(..., min_length=1, max_length=64)

# ---------- Endpoints CRUD ----------
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
    errors: List[Dict[str, Any]] = []

    identidad = _norm(payload.identidad)
    #identidad = identidad.lower() if identidad else None
    nfc_tag = _norm(payload.nfc_tag)
    nfc_tag = nfc_tag.lower() if nfc_tag else None

    tipo_req = (payload.tipo or "").strip()
    _validar_tipo(tipo_req, errors)
    tipo_final = TIPOS_CANONICOS.get(tipo_req.lower(), tipo_req)

    if payload.seccion_id is not None and not db.get(Seccion, payload.seccion_id):
        errors.append({"loc": ["body", "seccion_id"], "msg": "Sección inexistente", "type": "value_error.foreign_key"})
    if payload.ubicacion_id is not None and not db.get(Ubicacion, payload.ubicacion_id):
        errors.append({"loc": ["body", "ubicacion_id"], "msg": "Ubicación inexistente", "type": "value_error.foreign_key"})

    if payload.seccion_id is not None and payload.ubicacion_id is not None:
        u = db.get(Ubicacion, payload.ubicacion_id)
        if u and u.seccion_id and u.seccion_id != payload.seccion_id:
            errors.append({
                "loc": ["body", "ubicacion_id"],
                "msg": "La ubicación no pertenece a la sección indicada",
                "type": "value_error"
            })

    if identidad:
        if db.exec(select(Equipo).where(func.lower(Equipo.identidad) == identidad.lower())).first():
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
        notas=_norm(payload.notas), # <--- ASIGNAR NOTAS
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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    seccion_id: Optional[int] = Query(None, gt=0),
    ubicacion_id: Optional[int] = Query(None, gt=0),
    estado: Optional[EstadoEquipo] = Query(None),
    estados: Optional[str] = Query(None),
    ordenar: Optional[str] = Query("id_desc"),
    identidad_eq: Optional[str] = Query(None),
    nfc_tag_eq: Optional[str] = Query(None),
):
    if ordenar not in ALLOWED_ORDEN:
        _raise_422([{
            "loc": ["query", "ordenar"],
            "msg": f"Orden inválido. Válidos: {', '.join(sorted(ALLOWED_ORDEN))}",
            "type": "value_error"
        }])

    stmt = select(Equipo)
    count_stmt = select(func.count()).select_from(Equipo)

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
        stmt = stmt.where(*conds)
        count_stmt = count_stmt.where(*conds)

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
    else:
        stmt = stmt.order_by(Equipo.id.desc())

    total = db.exec(count_stmt).one()
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
    obj = db.get(Equipo, equipo_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")

    errors: List[Dict[str, Any]] = []

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

    if payload.seccion_id is not None and not db.get(Seccion, payload.seccion_id):
        errors.append({"loc": ["body", "seccion_id"], "msg": "Sección inexistente", "type": "value_error.foreign_key"})
    if payload.ubicacion_id is not None and not db.get(Ubicacion, payload.ubicacion_id):
        errors.append({"loc": ["body", "ubicacion_id"], "msg": "Ubicación inexistente", "type": "value_error.foreign_key"})

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

    identidad = _norm(payload.identidad) if payload.identidad is not None else None
    #identidad = identidad.lower() if identidad else None
    nfc_tag = _norm(payload.nfc_tag) if payload.nfc_tag is not None else None
    nfc_tag = nfc_tag.lower() if nfc_tag else None

    if identidad is not None and identidad.lower() != (obj.identidad.lower() if obj.identidad else None):
        if db.exec(select(Equipo).where(func.lower(Equipo.identidad) == identidad.lower())).first():
            errors.append({"loc": ["body", "identidad"], "msg": "identidad ya existe", "type": "value_error.unique"})
    
    if nfc_tag is not None and nfc_tag != (obj.nfc_tag.lower() if obj.nfc_tag else None):
        if db.exec(select(Equipo).where(func.lower(Equipo.nfc_tag) == nfc_tag)).first():
            errors.append({"loc": ["body", "nfc_tag"], "msg": "nfc_tag ya existe", "type": "value_error.unique"})

    if errors:
        _raise_422(errors)

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
    if payload.notas is not None: # <--- ACTUALIZAR NOTAS
        obj.notas = _norm(payload.notas)

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
    obj = db.get(Equipo, equipo_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")

    try:
        db.delete(obj)
        db.commit()
        return 
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
    total = db.exec(select(func.count(Equipo.id))).one()

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

# --- SECCIÓN NUEVA: ADJUNTOS EQUIPO (INVENTARIO) ---

@router.post(
    "/{equipo_id}/adjuntos",
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
    status_code=status.HTTP_201_CREATED
)
async def subir_adjunto_equipo(
    equipo_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    eq = db.get(Equipo, equipo_id)
    if not eq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")
        
    file_data = await FileManager.save_file(file, "equipos", f"eq_{eq.id}")
    
    adjunto = EquipoAdjunto(
        equipo_id=eq.id,
        nombre_archivo=file_data["nombre_archivo"],
        ruta_relativa=file_data["ruta_relativa"],
        content_type=file_data["content_type"],
        tamano_bytes=file_data["tamano_bytes"],
        subido_por_id=int(user["id"]) if user else None
    )
    
    db.add(adjunto)
    db.commit()
    db.refresh(adjunto)
    return adjunto

@router.get(
    "/{equipo_id}/adjuntos",
    dependencies=[Depends(current_user)]
)
def listar_adjuntos_equipo(
    equipo_id: int,
    db: Session = Depends(get_db),
):
    eq = db.get(Equipo, equipo_id)
    if not eq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")
        
    adjuntos = db.exec(
        select(EquipoAdjunto).where(EquipoAdjunto.equipo_id == equipo_id)
    ).all()
    
    return [
        {
            "id": a.id,
            "nombre_archivo": a.nombre_archivo,
            "url": f"/api/v1/equipos/{equipo_id}/adjuntos/{a.id}",
            "tipo": a.content_type,
            "tamano": a.tamano_bytes
        }
        for a in adjuntos
    ]

@router.get(
    "/{equipo_id}/adjuntos/{adjunto_id}",
    response_class=FileResponse,
    dependencies=[Depends(current_user)]
)
def descargar_adjunto_equipo(
    equipo_id: int,
    adjunto_id: int,
    db: Session = Depends(get_db)
):
    adj = db.get(EquipoAdjunto, adjunto_id)
    if not adj or adj.equipo_id != equipo_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Adjunto no encontrado")
        
    path = FileManager.get_path(adj.ruta_relativa)
    if not path.is_file():
         raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo físico no encontrado")
         
    return FileResponse(
        path,
        media_type=adj.content_type or "application/octet-stream",
        filename=adj.nombre_archivo
    )

@router.delete(
    "/{equipo_id}/adjuntos/{adjunto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))]
)
def eliminar_adjunto_equipo(
    equipo_id: int,
    adjunto_id: int,
    db: Session = Depends(get_db)
):
    adj = db.get(EquipoAdjunto, adjunto_id)
    if not adj or adj.equipo_id != equipo_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Adjunto no encontrado")
        
    FileManager.delete_file(adj.ruta_relativa)
    db.delete(adj)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)