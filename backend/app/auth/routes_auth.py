from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from app.core.deps import get_db
from app.core.security import verify_password, hash_password, make_access_token
from app.models.usuario import Usuario

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginIn(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.exec(select(Usuario).where(Usuario.username == data.username)).first()
    if not user or not verify_password(data.password, user.password_hash) or not user.active:
        raise HTTPException(401, "Credenciales inválidas")
    token = make_access_token(str(user.id), user.role)
    return {"access_token": token, "token_type": "bearer", "role": user.role}
