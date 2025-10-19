from typing import Generator
from fastapi import Depends, HTTPException, Request
from jose import jwt, JWTError
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session  # debe YIELDear sqlmodel.Session

def get_db() -> Generator[Session, None, None]:
    # Propaga el generator de la capa de datos
    yield from get_session()

def current_user(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")

    token = auth.split(" ", 1)[1]

    # Si AUDIENCE/ISSUER están vacíos, desactiva su verificación
    decode_kwargs = {
        "algorithms": [getattr(settings, "JWT_ALGORITHM", "HS256") or "HS256"],
        "key": settings.SECRET_KEY,
    }
    audience = getattr(settings, "AUDIENCE", None)
    issuer = getattr(settings, "ISSUER", None)
    if audience:
        decode_kwargs["audience"] = audience
    if issuer:
        decode_kwargs["issuer"] = issuer
    if not audience:
        decode_kwargs.setdefault("options", {})["verify_aud"] = False

    try:
        payload = jwt.decode(**decode_kwargs, token=token)
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Token inválido") from e

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sin 'sub'")

    request.state.user_id = user_id
    return {"id": user_id, "role": payload.get("role", "OPERARIO")}

def require_role(*roles: str):
    def dep(user=Depends(current_user)):
        if roles and user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return user
    return dep
