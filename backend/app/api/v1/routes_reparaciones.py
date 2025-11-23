from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Response,
    Request,
    Query,
    UploadFile,
    File,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func, select as sa_select
from sqlalchemy.exc import IntegrityError, DBAPIError, OperationalError

from app.core.deps import get_db, current_user, require_role
from app.models.equipo import Equipo
from app.models.reparacion import Reparacion
from app.models.reparacion_factura import ReparacionFactura
from app.core.config import settings

router = APIRouter(prefix="/reparaciones", tags=["reparaciones"])

# ----------------- Constantes / helpers -----------------
EstadoReparacion = Literal["ABIERTA", "EN_PROGRESO", "CERRADA"]
ALLOWED_ORDEN = {
    "id_asc",
    "id_desc",
    "inicio_asc",
    "inicio_desc",
    "estado_asc",
    "estado_desc",
}

# Directorio base donde se guardan las facturas en disco
FACTURAS_BASE_DIR = Path(settings.FACTURAS_DIR).resolve()
FACTURAS_BASE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_FACTURA_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

MAX_FACTURA_SIZE_MB = 20  # límite "sano" para evitar barbaridades


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
        errors.append(
            {
                "loc": ["body", "estado"],
                "msg": "No se puede reabrir una reparación cerrada desde este endpoint. Usa /{id}/reabrir",
                "type": "value_error",
            }
        )
    if actual == "ABIERTA" and nuevo not in {"ABIERTA", "EN_PROGRESO", "CERRADA"}:
        errors.append(
            {"loc": ["body", "estado"], "msg": "Transición inválida", "type": "value_error"}
        )
    if actual == "EN_PROGRESO" and nuevo not in {"EN_PROGRESO", "CERRADA"}:
        errors.append(
            {"loc": ["body", "estado"], "msg": "Transición inválida", "type": "value_error"}
        )


def _build_factura_filename(rep_id: int, original_filename: Optional[str]) -> str:
    """
    Genera un nombre de fichero "seguro" para guardar la factura en disco.
    Ejemplo: rep_12_8f2b3c4d5e.pdf
    """
    orig = original_filename or "factura"
    ext = Path(orig).suffix or ""
    uid = uuid4().hex
    return f"rep_{rep_id}_{uid}{ext}"


def _get_factura_path(relative_name: str) -> Path:
    """
    Devuelve la ruta absoluta a partir del nombre relativo guardado en BD.
    """
    return FACTURAS_BASE_DIR / relative_name


# ----------------- Schemas -----------------
class ReparacionCreateIn(BaseModel):
    equipo_id: int = Field(..., gt=0, examples=[1])
    incidencia_id: int = Field(..., gt=0, examples=[1])
    titulo: str = Field(..., min_length=3, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=8000)
    # opcionalmente permitir abrir ya EN_PROGRESO
    estado: Optional[EstadoReparacion] = Field(None, examples=["ABIERTA"])

    # Costes opcionales ya en el alta
    coste_materiales: Optional[float] = Field(None, ge=0)
    coste_mano_obra: Optional[float] = Field(None, ge=0)
    coste_otros: Optional[float] = Field(None, ge=0)
    moneda: Optional[str] = Field("EUR", min_length=3, max_length=3)
    proveedor: Optional[str] = Field(None, max_length=150)
    numero_factura: Optional[str] = Field(None, max_length=50)


class ReparacionUpdateIn(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=8000)
    estado: Optional[EstadoReparacion] = Field(None)

    coste_materiales: Optional[float] = Field(None, ge=0)
    coste_mano_obra: Optional[float] = Field(None, ge=0)
    coste_otros: Optional[float] = Field(None, ge=0)
    moneda: Optional[str] = Field(None, min_length=3, max_length=3)
    proveedor: Optional[str] = Field(None, max_length=150)
    numero_factura: Optional[str] = Field(None, max_length=50)


class ReparacionCerrarIn(BaseModel):
    fecha_fin: Optional[datetime] = Field(
        None, description="Si no se envía, se usa 'now()' (UTC)"
    )


class ReparacionFacturaOut(BaseModel):
    id: int
    nombre_archivo: str
    ruta_relativa: str
    content_type: Optional[str]
    tamano_bytes: Optional[int]
    es_principal: bool
    subido_en: datetime

    class Config:
        from_attributes = True


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
        errors.append(
            {
                "loc": ["body", "equipo_id"],
                "msg": "Equipo inexistente",
                "type": "value_error.foreign_key",
            }
        )

    from app.models.incidencia import Incidencia  # import local para evitar ciclos

    incidencia = db.get(Incidencia, payload.incidencia_id)
    if not incidencia:
        errors.append(
            {
                "loc": ["body", "incidencia_id"],
                "msg": "Incidencia inexistente",
                "type": "value_error.foreign_key",
            }
        )
    elif incidencia.equipo_id != payload.equipo_id:
        errors.append(
            {
                "loc": ["body", "incidencia_id"],
                "msg": "La incidencia no pertenece a ese equipo",
                "type": "value_error",
            }
        )

    estado = payload.estado or "ABIERTA"
    # No permitir crear directamente 'CERRADA'
    if estado not in {"ABIERTA", "EN_PROGRESO"}:
        errors.append(
            {
                "loc": ["body", "estado"],
                "msg": "Estado inicial inválido",
                "type": "value_error",
            }
        )

    if errors:
        _raise_422(errors)

    rep = Reparacion(
        equipo_id=payload.equipo_id,
        incidencia_id=payload.incidencia_id,
        titulo=_norm(payload.titulo),
        descripcion=_norm(payload.descripcion),
        estado=estado,
        usuario_id=int(user["id"]) if user and user.get("id") else None,
        coste_materiales=payload.coste_materiales,
        coste_mano_obra=payload.coste_mano_obra,
        coste_otros=payload.coste_otros,
        moneda=_norm(payload.moneda) if payload.moneda else None,
        proveedor=_norm(payload.proveedor),
        numero_factura=_norm(payload.numero_factura),
    )

    try:
        db.add(rep)
        db.commit()
        db.refresh(rep)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Conflicto de integridad (FK/índices)"
        )
    except DBAPIError:
        db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos"
        )

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
    desde: Optional[datetime] = Query(
        None, description="Fecha inicio >= (ISO-8601, UTC)"
    ),
    hasta: Optional[datetime] = Query(
        None, description="Fecha inicio <= (ISO-8601, UTC)"
    ),
    ordenar: str = Query(
        "inicio_desc",
        description="id_asc|id_desc|inicio_asc|inicio_desc|estado_asc|estado_desc",
    ),
):
    if ordenar not in ALLOWED_ORDEN:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "loc": ["query", "ordenar"],
                    "msg": f"Orden inválido. Válidos: {', '.join(sorted(ALLOWED_ORDEN))}",
                    "type": "value_error",
                }
            ],
        )
    if desde and hasta and desde > hasta:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Rango de fechas inválido (desde > hasta)"
        )

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
        validos = [e for e in lista if e in ("ABIERTA", "EN_PROGRESO", "CERRADA")]
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
    # 👇 IMPORTANTE: quitamos response_model_exclude_none aquí
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

    total = (
        db.exec(
            select(func.count())
            .select_from(Reparacion)
            .where(Reparacion.equipo_id == equipo_id)
        )
        .scalar_one()
    )
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
        # Bloqueo + obtención como instancia ORM
        rep_db = (
            db.exec(
                sa_select(Reparacion)
                .where(Reparacion.id == rep.id)
                .with_for_update()
            )
            .scalar_one()
        )

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

        # Costes / datos de factura
        if payload.coste_materiales is not None:
            rep_db.coste_materiales = payload.coste_materiales
        if payload.coste_mano_obra is not None:
            rep_db.coste_mano_obra = payload.coste_mano_obra
        if payload.coste_otros is not None:
            rep_db.coste_otros = payload.coste_otros
        if payload.moneda is not None:
            rep_db.moneda = _norm(payload.moneda)
        if payload.proveedor is not None:
            rep_db.proveedor = _norm(payload.proveedor)
        if payload.numero_factura is not None:
            rep_db.numero_factura = _norm(payload.numero_factura)

        if hasattr(rep_db, "usuario_modificador_id") and user and user.get("id"):
            rep_db.usuario_modificador_id = int(user["id"])

        db.add(rep_db)
        db.commit()
        db.refresh(rep_db)
        return rep_db

    except OperationalError:
        db.rollback()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Error temporal de base de datos"
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad")
    except DBAPIError:
        db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos"
        )


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
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "fecha_fin no puede ser anterior a fecha_inicio",
        )

    try:
        # Bloqueo + instancia ORM
        rep_db = (
            db.exec(
                sa_select(Reparacion)
                .where(Reparacion.id == rep.id)
                .with_for_update()
            )
            .scalar_one()
        )

        rep_db.estado = "CERRADA"
        rep_db.fecha_fin = fecha_fin
        if hasattr(rep_db, "cerrada_por_id") and user and user.get("id"):
            rep_db.cerrada_por_id = int(user["id"])

        db.add(rep_db)
        db.commit()
        db.refresh(rep_db)
        return rep_db

    except OperationalError:
        db.rollback()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Error temporal de base de datos"
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Conflicto de integridad (FK/índices)"
        )
    except DBAPIError:
        db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos"
        )


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
        raise HTTPException(
            status.HTTP_409_CONFLICT, "La reparación no está cerrada"
        )

    try:
        # Bloqueo + instancia ORM
        rep_db = (
            db.exec(
                sa_select(Reparacion)
                .where(Reparacion.id == rep.id)
                .with_for_update()
            )
            .scalar_one()
        )

        rep_db.estado = "ABIERTA"
        rep_db.fecha_fin = None
        if hasattr(rep_db, "cerrada_por_id"):
            rep_db.cerrada_por_id = None
        if hasattr(rep_db, "usuario_modificador_id") and user and user.get("id"):
            rep_db.usuario_modificador_id = int(user["id"])

        db.add(rep_db)
        db.commit()
        db.refresh(rep_db)
        return rep_db

    except OperationalError:
        db.rollback()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Error temporal de base de datos"
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de integridad")
    except DBAPIError:
        db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos"
        )


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

    # Borrar también archivos físicos de todas las facturas asociadas
    facturas = db.exec(
        select(ReparacionFactura).where(ReparacionFactura.reparacion_id == reparacion_id)
    ).all()
    for fac in facturas:
        try:
            (_get_factura_path(fac.ruta_relativa)).unlink(missing_ok=True)
        except OSError:
            pass

    # También podemos intentar borrar el archivo principal si apunta a algo suelto
    if rep.factura_archivo_path:
        try:
            (_get_factura_path(rep.factura_archivo_path)).unlink(missing_ok=True)
        except OSError:
            pass

    try:
        db.delete(rep)
        db.commit()
        return
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede eliminar la reparación (restricciones)",
        )
    except DBAPIError:
        db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos"
        )


# ----------------- Subida / descarga de factura (principal y múltiples) -----------------
@router.post(
    "/{reparacion_id}/factura",
    response_model=Reparacion,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
async def subir_factura_reparacion(
    reparacion_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Sube una factura asociada a la reparación.
    - Crea un registro en `reparacion_factura`.
    - Marca esa factura como principal vía campos factura_* en Reparacion.
    """
    rep = db.get(Reparacion, reparacion_id)
    if not rep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparación no encontrada")

    if not file.filename:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Archivo sin nombre")

    if file.content_type not in ALLOWED_FACTURA_MIMES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Tipo de archivo no permitido. Permitidos: {', '.join(ALLOWED_FACTURA_MIMES)}",
        )

    new_name = _build_factura_filename(rep.id, file.filename)
    dest_path = _get_factura_path(new_name)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Guardado en disco (streaming)
    max_bytes = MAX_FACTURA_SIZE_MB * 1024 * 1024
    written = 0
    try:
        with dest_path.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    f.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        f"Archivo demasiado grande (máx {MAX_FACTURA_SIZE_MB} MB)",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        try:
            dest_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Error guardando el archivo de factura",
        )

    user_id = int(user["id"]) if user and user.get("id") else None

    try:
        # Crear nueva factura
        factura = ReparacionFactura(
            reparacion_id=rep.id,
            nombre_archivo=file.filename or new_name,
            ruta_relativa=new_name,
            content_type=file.content_type,
            tamano_bytes=written,
            subido_por_id=user_id,
        )
        db.add(factura)

        # Actualizar campos "principal" en Reparacion
        rep.factura_archivo_nombre = factura.nombre_archivo
        rep.factura_archivo_path = factura.ruta_relativa
        rep.factura_content_type = factura.content_type
        rep.factura_tamano_bytes = factura.tamano_bytes
        if hasattr(rep, "usuario_modificador_id") and user_id:
            rep.usuario_modificador_id = user_id

        db.add(rep)
        db.commit()
        db.refresh(rep)
        return rep

    except DBAPIError:
        db.rollback()
        try:
            dest_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Error interno de base de datos al asociar la factura",
        )


@router.get(
    "/{reparacion_id}/factura",
    response_class=FileResponse,
    dependencies=[Depends(current_user)],
)
def descargar_factura_reparacion(
    reparacion_id: int,
    db: Session = Depends(get_db),
):
    """
    Devuelve el archivo de factura principal asociado a la reparación.
    Si no hay principal, intenta usar la última factura existente.
    """
    rep = db.get(Reparacion, reparacion_id)
    if not rep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparación no encontrada")

    # Prioridad: campos de Reparacion (principal)
    ruta = rep.factura_archivo_path

    if not ruta:
        # Intentar buscar una factura cualquiera y usarla
        fac = db.exec(
            select(ReparacionFactura)
            .where(ReparacionFactura.reparacion_id == reparacion_id)
            .order_by(ReparacionFactura.subido_en.desc(), ReparacionFactura.id.desc())
        ).first()
        if not fac:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "La reparación no tiene factura adjunta"
            )
        ruta = fac.ruta_relativa

    file_path = _get_factura_path(ruta)
    if not file_path.is_file():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No se encuentra el archivo de factura en el servidor",
        )

    return FileResponse(
        file_path,
        media_type=rep.factura_content_type or "application/pdf",
        filename=rep.factura_archivo_nombre or file_path.name,
    )


@router.get(
    "/{reparacion_id}/facturas",
    response_model=List[ReparacionFacturaOut],
    dependencies=[Depends(current_user)],
)
def listar_facturas_reparacion(
    reparacion_id: int,
    db: Session = Depends(get_db),
):
    """
    Lista todas las facturas asociadas a una reparación.
    Devuelve siempre los campos:
    id, nombre_archivo, ruta_relativa, content_type, tamano_bytes, es_principal, subido_en
    """
    rep = db.get(Reparacion, reparacion_id)
    if not rep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparación no encontrada")

    facturas = db.exec(
        select(ReparacionFactura)
        .where(ReparacionFactura.reparacion_id == reparacion_id)
        .order_by(ReparacionFactura.subido_en.desc(), ReparacionFactura.id.desc())
    ).all()

    principal_path = rep.factura_archivo_path

    # Serialización explícita para asegurar claves exactas en el JSON
    return [
        ReparacionFacturaOut(
            id=fac.id,
            nombre_archivo=fac.nombre_archivo,
            ruta_relativa=fac.ruta_relativa,
            content_type=fac.content_type,
            tamano_bytes=fac.tamano_bytes,
            es_principal=bool(principal_path and fac.ruta_relativa == principal_path),
            subido_en=fac.subido_en,
        )
        for fac in facturas
    ]


@router.get(
    "/{reparacion_id}/facturas/{factura_id}",
    response_class=FileResponse,
    dependencies=[Depends(current_user)],
)
def descargar_factura_concreta(
    reparacion_id: int,
    factura_id: int,
    db: Session = Depends(get_db),
):
    """
    Descarga una factura concreta de una reparación.
    """
    factura = db.get(ReparacionFactura, factura_id)
    if not factura or factura.reparacion_id != reparacion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Factura no encontrada para esa reparación")

    file_path = _get_factura_path(factura.ruta_relativa)
    if not file_path.is_file():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No se encuentra el archivo de factura en el servidor",
        )

    return FileResponse(
        file_path,
        media_type=factura.content_type or "application/octet-stream",
        filename=factura.nombre_archivo or file_path.name,
    )


@router.delete(
    "/{reparacion_id}/facturas/{factura_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))],
)
def eliminar_factura_concreta(
    reparacion_id: int,
    factura_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Elimina una factura concreta (BD + fichero físico).
    Si era la factura principal, reasigna otra como principal si existe.
    """
    rep = db.get(Reparacion, reparacion_id)
    if not rep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparación no encontrada")

    factura = db.get(ReparacionFactura, factura_id)
    if not factura or factura.reparacion_id != reparacion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Factura no encontrada")

    file_path = _get_factura_path(factura.ruta_relativa)
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        pass

    # Si era la principal, necesitamos actualizar la referencia en Reparacion
    if rep.factura_archivo_path == factura.ruta_relativa:
        otra = db.exec(
            select(ReparacionFactura)
            .where(
                ReparacionFactura.reparacion_id == reparacion_id,
                ReparacionFactura.id != factura.id,
            )
            .order_by(ReparacionFactura.subido_en.desc(), ReparacionFactura.id.desc())
        ).first()

        if otra:
            rep.factura_archivo_nombre = otra.nombre_archivo
            rep.factura_archivo_path = otra.ruta_relativa
            rep.factura_content_type = otra.content_type
            rep.factura_tamano_bytes = otra.tamano_bytes
            db.add(otra)
        else:
            rep.factura_archivo_nombre = None
            rep.factura_archivo_path = None
            rep.factura_content_type = None
            rep.factura_tamano_bytes = None

    db.delete(factura)
    db.add(rep)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
