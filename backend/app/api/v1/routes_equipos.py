from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Equipo

router = APIRouter(prefix="/equipos", tags=["equipos"])

@router.post("/", response_model=Equipo)
def crear_equipo(payload: Equipo, db: Session = Depends(get_session)):
    # Unicidad simple (identidad/nfc_tag)
    if payload.identidad:
        existe = db.exec(select(Equipo).where(Equipo.identidad == payload.identidad)).first()
        if existe:
            raise HTTPException(400, "identidad ya existe")

    if payload.nfc_tag:
        existe = db.exec(select(Equipo).where(Equipo.nfc_tag == payload.nfc_tag)).first()
        if existe:
            raise HTTPException(400, "nfc_tag ya existe")

    db.add(payload)
    db.commit()
    db.refresh(payload)
    return payload

@router.get("/", response_model=list[Equipo])
def listar_equipos(db: Session = Depends(get_session)):
    return db.exec(select(Equipo)).all()

@router.get("/{equipo_id}", response_model=Equipo)
def obtener_equipo(equipo_id: int, db: Session = Depends(get_session)):
    obj = db.get(Equipo, equipo_id)
    if not obj:
        raise HTTPException(404, "Equipo no encontrado")
    return obj
