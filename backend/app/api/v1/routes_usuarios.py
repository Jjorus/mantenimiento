# backend/app/api/v1/routes_usuarios.py
from typing import Optional, List, Literal, get_args
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from pydantic import BaseModel, Field, EmailStr
from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, DBAPIError

from app.core.deps import get_db, current_user, require_role
from app.core.security import hash_password
from app.models.usuario import Usuario

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

RoleLiteral = Literal["ADMIN", "MANTENIMIENTO", "OPERARIO"]


# ---------------------------
# Schemas
# ---------------------------
class UsuarioOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: RoleLiteral
    active: bool
    class Config:
        from_attributes = True


class UsuarioCreateIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["jdoe"])
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: RoleLiteral = "OPERARIO"
    active: bool = True


class UsuarioUpdateIn(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[RoleLiteral] = None
    active: Optional[bool] = None


class PasswordChangeIn(BaseModel):
    password: str = Field(..., min_length=6)


# ---------------------------
# Helpers
# ---------------------------
def _last_admin_guard(db: Session, exclude_user_id: Optional[int] = None) -> bool:
    """
    True si EXISTE al menos un ADMIN diferente de exclude_user_id.
    Úsalo antes de desactivar, bajar de rol o borrar a un admin.
    """
    stmt = select(func.count()).select_from(Usuario).where(Usuario.role == "ADMIN", Usuario.active == True)  # noqa: E712
    if exclude_user_id is not None:
        stmt = stmt.where(Usuario.id != exclude_user_id)
    count = db.exec(stmt).one()
    return count > 0


# ---------------------------
# /me (autogestión)
# ---------------------------
@router.get("/me", response_model=UsuarioOut, response_model_exclude_none=True, dependencies=[Depends(current_user)])
def me(user=Depends(current_user), db: Session = Depends(get_db)):
    u = db.get(Usuario, int(user["id"]))
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return u


@router.patch("/me", response_model=UsuarioOut, response_model_exclude_none=True, dependencies=[Depends(current_user)])
def update_me(payload: UsuarioUpdateIn, user=Depends(current_user), db: Session = Depends(get_db)):
    """
    Permite cambiar SOLO el email del propio usuario.
    (No permite role ni active aquí).
    """
    u = db.get(Usuario, int(user["id"]))
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    if payload.role is not None or payload.active is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes cambiar rol ni estado desde /me")

    if payload.email is not None:
        u.email = str(payload.email).strip()

    try:
        db.add(u)
        db.commit()
        db.refresh(u)
        return u
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email ya en uso")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(current_user)])
def change_my_password(payload: PasswordChangeIn, user=Depends(current_user), db: Session = Depends(get_db)):
    u = db.get(Usuario, int(user["id"]))
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    u.password_hash = hash_password(payload.password)
    db.add(u)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------
# Admin: gestión de usuarios
# ---------------------------
@router.post(
    "",
    response_model=UsuarioOut,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("ADMIN"))],
)
def create_user(payload: UsuarioCreateIn, db: Session = Depends(get_db)):
    u = Usuario(
        username=payload.username.strip(),
        email=str(payload.email).strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        active=payload.active,
    )
    try:
        db.add(u)
        db.commit()
        db.refresh(u)
        return u
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Usuario o email ya existen")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")


@router.get(
    "",
    response_model=List[UsuarioOut],
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("ADMIN"))],
)
def list_users(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None, description="Busca en username/email (contiene)"),
    role: Optional[RoleLiteral] = Query(None),
    active: Optional[bool] = Query(None),
):
    stmt = select(Usuario)
    count_stmt = select(func.count()).select_from(Usuario)

    conds = []
    if q:
        like = f"%{q.strip()}%"
        conds.append(Usuario.username.ilike(like) | Usuario.email.ilike(like))
    if role:
        conds.append(Usuario.role == role)
    if active is not None:
        conds.append(Usuario.active == active)

    if conds:
        for c in conds:
            stmt = stmt.where(c)
            count_stmt = count_stmt.where(c)

    stmt = stmt.order_by(Usuario.id.desc())

    total = db.exec(count_stmt).one()
    response.headers["X-Total-Count"] = str(total)

    stmt = stmt.limit(limit).offset(offset)
    return db.exec(stmt).all()


@router.get(
    "/{user_id}",
    response_model=UsuarioOut,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("ADMIN"))],
)
def get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(Usuario, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return u


@router.patch(
    "/{user_id}",
    response_model=UsuarioOut,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("ADMIN"))],
)
def update_user(user_id: int, payload: UsuarioUpdateIn, db: Session = Depends(get_db)):
    u = db.get(Usuario, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    # Si se intenta quitar el último ADMIN (desactivando o cambiando rol) -> bloquear
    if u.role == "ADMIN":
        demote = payload.role is not None and payload.role != "ADMIN"
        deactivate = payload.active is not None and payload.active is False
        if (demote or deactivate) and not _last_admin_guard(db, exclude_user_id=user_id):
            raise HTTPException(status.HTTP_409_CONFLICT, "No puedes dejar el sistema sin ningún ADMIN activo")

    if payload.email is not None:
        u.email = str(payload.email).strip()
    if payload.role is not None:
        u.role = payload.role
    if payload.active is not None:
        u.active = payload.active

    try:
        db.add(u)
        db.commit()
        db.refresh(u)
        return u
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email ya en uso")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")


@router.post(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("ADMIN"))],
)
def reset_password(user_id: int, payload: PasswordChangeIn, db: Session = Depends(get_db)):
    u = db.get(Usuario, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    u.password_hash = hash_password(payload.password)
    db.add(u)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("ADMIN"))],
)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(Usuario, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    # No borrar al último admin activo
    if u.role == "ADMIN" and u.active and not _last_admin_guard(db, exclude_user_id=user_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "No puedes borrar al último ADMIN activo")

    try:
        db.delete(u)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except DBAPIError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno de base de datos")
