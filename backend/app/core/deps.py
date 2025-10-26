# app/core/deps.py
from typing import Generator, Any, Dict, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session  # YIELDea una sqlmodel.Session

# Esquema de autenticación para Swagger/Docs (Botón "Authorize" => Bearer <token>)
security = HTTPBearer(auto_error=True)


def get_db() -> Generator[Session, None, None]:
    # Propaga el generator de la capa de datos
    yield from get_session()


def _decode_token(token: str) -> Dict[str, Any]:
    key = settings.SECRET_KEY.get_secret_value()
    algorithms = [getattr(settings, "JWT_ALGORITHM", "HS256") or "HS256"]

    # Verificaciones condicionales según lo configurado
    options: Dict[str, Any] = {}
    decode_kwargs: Dict[str, Any] = {
        "algorithms": algorithms,
        "options": options,
    }
    if settings.ISSUER:
        decode_kwargs["issuer"] = settings.ISSUER
    if settings.AUDIENCE:
        decode_kwargs["audience"] = settings.AUDIENCE
    else:
        # Si no hay AUDIENCE, desactiva verificación 'aud'
        options["verify_aud"] = False

    # jose.jwt.decode(token, key, algorithms=..., issuer=..., audience=..., options=...)
    return jwt.decode(token, key, **decode_kwargs)


def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Extrae el token Bearer del header Authorization, lo valida y devuelve:
      { "id": <sub>, "role": <ROLE> }
    """
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    token = creds.credentials
    try:
        payload = _decode_token(token)
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from e

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin 'sub'")

    role = (payload.get("role") or "OPERARIO").upper()
    return {"id": sub, "role": role}


def require_role(*roles: str) -> Callable:
    """
    Dependencia para proteger endpoints por rol.
    - Si el usuario es ADMIN, pasa siempre.
    - Si se pasan roles, el usuario debe pertenecer a alguno.
    """
    roles_up = {r.upper() for r in roles}

    def dep(user: Dict[str, Any] = Depends(current_user)):
        role = user.get("role", "").upper()
        if role == "ADMIN":
            return user
        if roles_up and role not in roles_up:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
        return user

    return dep
