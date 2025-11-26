# backend/app/api/v1/routes_incidencias.py
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response, Request, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func, select as sa_select
from sqlalchemy.exc import IntegrityError, DBAPIError, OperationalError

from app.core.deps import get_db, current_user, require_role
from app.core.file_manager import FileManager
from app.models.incidencia import Incidencia
from app.models.equipo import Equipo
from app.models.incidencia_adjunto import IncidenciaAdjunto

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

# ---------- Endpoints CRUD ----------
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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    estado: Optional[Estado] = Query(None),
    estados: Optional[str] = Query(None),
    equipo_id: Optional[int] = Query(None, gt=0),
    desde: datetime | None = Query(None),
    hasta: datetime | None = Query(None),
    ordenar: str = Query("fecha_desc"),
):
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
    obj = db.get(Incidencia, incidencia_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")

    try:
        # Bloqueo pesimista para evitar condiciones de carrera
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
        db.commit()  # FIX: Commit explícito para asegurar guardado
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
    obj = db.get(Incidencia, incidencia_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")

    try:
        inc_db = db.exec(
            sa_select(Incidencia).where(Incidencia.id == obj.id).with_for_update()
        ).scalar_one()

        if inc_db.estado != "CERRADA":
            inc_db.cerrar(int(user["id"]))
            db.add(inc_db)
            db.commit() # FIX: Commit explícito
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
    obj = db.get(Incidencia, incidencia_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")

    try:
        inc_db = db.exec(
            sa_select(Incidencia).where(Incidencia.id == obj.id).with_for_update()
        ).scalar_one()

        if inc_db.estado != "CERRADA":
            raise HTTPException(status.HTTP_409_CONFLICT, "La incidencia no está cerrada")

        inc_db.reabrir(int(user["id"]))
        db.add(inc_db)
        db.commit() # FIX: Commit explícito
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
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")

# --- ADJUNTOS INCIDENCIA ---

@router.post(
    "/{incidencia_id}/adjuntos",
    dependencies=[Depends(require_role("OPERARIO", "MANTENIMIENTO", "ADMIN"))],
    status_code=status.HTTP_201_CREATED
)
async def subir_adjunto_incidencia(
    incidencia_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    inc = db.get(Incidencia, incidencia_id)
    if not inc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")
        
    # Guardar en disco (carpeta 'incidencias')
    file_data = await FileManager.save_file(file, "incidencias", f"inc_{inc.id}")
    
    # Crear registro BD
    adjunto = IncidenciaAdjunto(
        incidencia_id=inc.id,
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
    "/{incidencia_id}/adjuntos",
    response_model=List[dict] 
)
def listar_adjuntos_incidencia(
    incidencia_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    inc = db.get(Incidencia, incidencia_id)
    if not inc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")
        
    adjuntos = db.exec(
        select(IncidenciaAdjunto).where(IncidenciaAdjunto.incidencia_id == incidencia_id)
    ).all()
    
    # Mapeo manual simple
    return [
        {
            "id": a.id,
            "nombre_archivo": a.nombre_archivo,
            "url": f"/api/v1/incidencias/{incidencia_id}/adjuntos/{a.id}", 
            "tipo": a.content_type,
            "tamano": a.tamano_bytes
        }
        for a in adjuntos
    ]

@router.get(
    "/{incidencia_id}/adjuntos/{adjunto_id}",
    response_class=FileResponse,
    dependencies=[Depends(current_user)]
)
def descargar_adjunto_incidencia(
    incidencia_id: int,
    adjunto_id: int,
    db: Session = Depends(get_db)
):
    adj = db.get(IncidenciaAdjunto, adjunto_id)
    if not adj or adj.incidencia_id != incidencia_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Adjunto no encontrado")
        
    path = FileManager.get_path(adj.ruta_relativa)
    if not path.is_file():
         raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo físico no encontrado en el servidor")
         
    return FileResponse(
        path,
        media_type=adj.content_type or "application/octet-stream",
        filename=adj.nombre_archivo
    )

@router.delete(
    "/{incidencia_id}/adjuntos/{adjunto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("MANTENIMIENTO", "ADMIN"))] # Solo ellos pueden borrar
)
def eliminar_adjunto_incidencia(
    incidencia_id: int,
    adjunto_id: int,
    db: Session = Depends(get_db)
):
    adj = db.get(IncidenciaAdjunto, adjunto_id)
    if not adj or adj.incidencia_id != incidencia_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Adjunto no encontrado")
        
    FileManager.delete_file(adj.ruta_relativa)
    db.delete(adj)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)