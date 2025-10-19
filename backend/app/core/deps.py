from fastapi import Depends, HTTPException, Request
from jose import jwt, JWTError
from app.core.config import settings
from app.core.db import get_session
from sqlmodel import Session

def get_db() -> Session:
    yield from get_session()

def current_user(request: Request):
    auth = request.headers.get("Authorization","")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "No autorizado")
    token = auth.split(" ",1)[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"],
                             audience=settings.AUDIENCE, issuer=settings.ISSUER)
    except JWTError:
        raise HTTPException(401, "Token inválido")
    request.state.user_id = payload["sub"]
    return {"id": payload["sub"], "role": payload.get("role","OPERARIO")}

def require_role(*roles):
    def dep(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Permisos insuficientes")
        return user
    return dep