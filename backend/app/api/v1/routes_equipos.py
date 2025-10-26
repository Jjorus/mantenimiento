from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.deps import get_db, current_user, require_role
from app.models.equipo import Equipo
from app.models.seccion import Seccion
from app.models.ubicacion import Ubicacion

router = APIRouter(prefix="/equipos", tags=["equipos"])


def _raise_422(errors: List[Dict[str, Any]]) -> None:
    """
    Lanza 422 con una lista de errores estilo Pydantic:
    [{"loc": ["body","campo"], "msg": "...", "type": "value_error.*"}, ...]
    """
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)


@router.post(
    "/",
    response_model=Equipo,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("ADMIN", "MANTENIMIENTO"))],
)
def crear_equipo(payload: Equipo, db: Session = Depends(get_db), user=Depends(current_user)):
    errors: List[Dict[str, Any]] = []

    # --- Unicidad (identidad / nfc_tag) ---
    if payload.identidad:
        existe = db.exec(select(Equipo).where(Equipo.identidad == payload.identidad)).first()
        if existe:
            errors.append({
                "loc": ["body", "identidad"],
                "msg": "identidad ya existe",
                "type": "value_error.unique",
            })

    if payload.nfc_tag:
        existe = db.exec(select(Equipo).where(Equipo.nfc_tag == payload.nfc_tag)).first()
        if existe:
            errors.append({
                "loc": ["body", "nfc_tag"],
                "msg": "nfc_tag ya existe",
                "type": "value_error.unique",
            })

    # --- FKs (seccion_id / ubicacion_id) ---
    if payload.seccion_id is not None:
        if not db.get(Seccion, payload.seccion_id):
            errors.append({
                "loc": ["body", "seccion_id"],
                "msg": "Sección inexistente",
                "type": "value_error.foreign_key",
            })

    if payload.ubicacion_id is not None:
        if not db.get(Ubicacion, payload.ubicacion_id):
            errors.append({
                "loc": ["body", "ubicacion_id"],
                "msg": "Ubicación inexistente",
                "type": "value_error.foreign_key",
            })

    if errors:
        _raise_422(errors)

    db.add(payload)
    db.commit()
    db.refresh(payload)
    return payload


@router.get("/", response_model=list[Equipo], dependencies=[Depends(current_user)])
def listar_equipos(db: Session = Depends(get_db)):
    return db.exec(select(Equipo)).all()


@router.get("/{equipo_id}", response_model=Equipo, dependencies=[Depends(current_user)])
def obtener_equipo(equipo_id: int, db: Session = Depends(get_db)):
    obj = db.get(Equipo, equipo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj
