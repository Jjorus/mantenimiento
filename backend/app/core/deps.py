# app/core/deps.py
from typing import Generator, Any, Dict, Callable
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session  # debe YIELDear sqlmodel.Session

# Si en main incluyes routers bajo prefix="/api", el login real es /api/auth/login
bearer_scheme = HTTPBearer(auto_error=True)

def get_db() -> Generator[Session, None, None]:
    yield from get_session()

def _decode_token(token: str) -> Dict[str, Any]:
    secret = settings.SECRET_KEY.get_secret_value()  # <-- importante
    algorithms = [getattr(settings, "JWT_ALGORITHM", "HS256") or "HS256"]

    decode_kwargs: Dict[str, Any] = {"algorithms": algorithms}
    # Verificaciones condicionales
    if settings.ISSUER:
        decode_kwargs["issuer"] = settings.ISSUER
    if settings.AUDIENCE:
        decode_kwargs["audience"] = settings.AUDIENCE
    else:
        decode_kwargs["options"] = {"verify_aud": False}

    # jose.jwt.decode(token, key, algorithms=..., issuer=..., audience=..., options=...)
    return jwt.decode(token, secret, **decode_kwargs)

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """
    Extrae el JWT del header Authorization (Bearer <token>), lo decodifica y
    devuelve un dict con el id de usuario y el rol en mayúsculas.

    Lanza 401 si el token no es válido o no contiene 'sub'.
    """
    token = credentials.credentials
    try:
        payload = _decode_token(token)  # usa SECRET_KEY, ISSUER/AUDIENCE condicionales
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin 'sub'")

    role = (payload.get("role") or "OPERARIO").upper()
    return {"id": sub, "role": role}

def require_role(*roles: str) -> Callable:
    roles_up = {r.upper() for r in roles}

    def dep(user: Dict[str, Any] = Depends(current_user)):
        role = user.get("role", "").upper()
        # ADMIN puede todo
        if role == "ADMIN":
            return user
        if roles_up and role not in roles_up:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
        return user

    return dep
