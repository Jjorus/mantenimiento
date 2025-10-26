from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.deps import get_db, current_user
from app.models.ubicacion import Ubicacion

router = APIRouter(prefix="/ubicaciones", tags=["ubicaciones"])

@router.get("/", response_model=list[Ubicacion], dependencies=[Depends(current_user)])
def list_ubicaciones(db: Session = Depends(get_db)):
    return db.exec(select(Ubicacion)).all()
