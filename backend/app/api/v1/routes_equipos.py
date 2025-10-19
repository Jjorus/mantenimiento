from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.deps import get_db, current_user
from app.models.equipo import Equipo

router = APIRouter(prefix="/equipos", tags=["equipos"])

@router.get("", response_model=list[Equipo])
def list_equipos(db: Session = Depends(get_db), user=Depends(current_user)):
    return db.exec(select(Equipo)).all()
