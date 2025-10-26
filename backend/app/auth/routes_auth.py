from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from jose import jwt
from pydantic import BaseModel, StringConstraints
from sqlmodel import Session, select

from app.core.config import settings
from app.core.deps import get_db, current_user, require_role
from app.core.security import hash_password, verify_password
from app.core.rate_limit import (
    is_locked,
    incr_login_fail,
    lock_if_needed,
    reset_login_counters_and_unlock,
)
from app.models.usuario import Usuario

router = APIRouter(prefix="/auth", tags=["auth"])

def _now() -> datetime:
    return datetime.now(timezone.utc)

def make_access_token(sub: str, role: str) -> tuple[str, int]:
    exp = _now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": sub,
        "role": role,
        "exp": exp,
    }
    # Añade iss/aud sólo si están configurados
    if settings.ISSUER:
        payload["iss"] = settings.ISSUER
    if settings.AUDIENCE:
        payload["aud"] = settings.AUDIENCE

    key = settings.SECRET_KEY.get_secret_value()
    token = jwt.encode(payload, key, algorithm=settings.JWT_ALGORITHM)
    return token, int(exp.timestamp())

# ===== Esquemas =====
UsernameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3)]
PasswordStr = Annotated[str, StringConstraints(min_length=6)]
RoleStr     = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3)]

class LoginIn(BaseModel):
    username: UsernameStr
    password: PasswordStr

class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    username: str
    expires_at: int

class MeOut(BaseModel):
    id: int
    username: str
    role: str
    active: bool

class UserCreateIn(BaseModel):
    username: UsernameStr
    password: PasswordStr
    role: RoleStr  # "ADMIN" | "MANTENIMIENTO" | "OPERARIO"
    active: bool = True

class UserPatchIn(BaseModel):
    password: Optional[PasswordStr] = None
    role: Optional[RoleStr] = None
    active: Optional[bool] = None

class ChangePasswordIn(BaseModel):
    current_password: PasswordStr
    new_password:     PasswordStr

# ===== Endpoints =====
@router.post("/login", response_model=LoginOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"

    # 1) ¿Bloqueado usuario o IP?
    locked, ttl, reason = is_locked(data.username, client_ip)
    if locked:
        raise HTTPException(
            status_code=429,
            detail=f"Cuenta bloqueada por intentos fallidos. Intenta de nuevo en {ttl} segundos.",
        )

    # 2) Credenciales
    user = db.exec(select(Usuario).where(Usuario.username == data.username)).first()
    ok = bool(user and user.active and verify_password(data.password, user.password_hash))

    if not ok:
        incr_login_fail(data.username, client_ip)
        now_locked, ttl2, _ = lock_if_needed(data.username, client_ip)
        if now_locked:
            raise HTTPException(
                status_code=429,
                detail=f"Cuenta bloqueada por intentos fallidos. Intenta de nuevo en {ttl2} segundos.",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    # 4) Éxito: limpia contadores y locks
    reset_login_counters_and_unlock(data.username, client_ip)

    # 5) Token
    token, exp_ts = make_access_token(str(user.id), user.role)
    return LoginOut(
        access_token=token,
        role=user.role,
        user_id=user.id,
        username=user.username,
        expires_at=exp_ts,
    )

@router.get("/me", response_model=MeOut)
def me(user=Depends(current_user), db: Session = Depends(get_db)):
    u = db.get(Usuario, int(user["id"]))
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return MeOut(id=u.id, username=u.username, role=u.role, active=u.active)

@router.post("/users", status_code=201, dependencies=[Depends(require_role("ADMIN"))])
def crear_usuario(data: UserCreateIn, db: Session = Depends(get_db)):
    role = data.role.upper()
    if role not in ("ADMIN", "MANTENIMIENTO", "OPERARIO"):
        raise HTTPException(422, detail="Rol inválido")

    exists = db.exec(select(Usuario).where(Usuario.username == data.username)).first()
    if exists:
        raise HTTPException(status_code=409, detail="Usuario ya existe")

    user = Usuario(
        username=data.username,
        password_hash=hash_password(data.password),
        role=role,
        active=data.active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "role": user.role, "active": user.active}

@router.get("/users", dependencies=[Depends(require_role("ADMIN"))])
def listar_usuarios(db: Session = Depends(get_db)):
    users = db.exec(select(Usuario)).all()
    return [{"id": u.id, "username": u.username, "role": u.role, "active": u.active} for u in users]

@router.patch("/users/{user_id}", dependencies=[Depends(require_role("ADMIN"))])
def actualizar_usuario(user_id: int, data: UserPatchIn, db: Session = Depends(get_db)):
    user = db.get(Usuario, user_id)
    if not user:
        raise HTTPException(404, detail="Usuario no encontrado")

    if data.password is not None:
        user.password_hash = hash_password(data.password)
    if data.role is not None:
        role = data.role.upper()
        if role not in ("ADMIN", "MANTENIMIENTO", "OPERARIO"):
            raise HTTPException(422, detail="Rol inválido")
        user.role = role
    if data.active is not None:
        user.active = data.active

    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "role": user.role, "active": user.active}

@router.post("/change-password")
def change_password(payload: ChangePasswordIn, user=Depends(current_user), db: Session = Depends(get_db)):
    u = db.get(Usuario, int(user["id"]))
    if not u:
        raise HTTPException(404, detail="Usuario no encontrado")
    if not verify_password(payload.current_password, u.password_hash):
        raise HTTPException(401, detail="Contraseña actual incorrecta")
    u.password_hash = hash_password(payload.new_password)
    db.add(u)
    db.commit()
    return {"ok": True}
