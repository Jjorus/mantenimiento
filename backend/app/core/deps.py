# app/core/deps.py
from typing import Generator, Any, Dict, Callable, Optional

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.db import get_session
from app.models.usuario import Usuario
from app.core.security import (
    decode_token,
    is_revoked,
    validate_token_type,
)

# ----- logger (para diagnóstico temporal) -----
logger = logging.getLogger("auth.deps")

# ----- Seguridad para Swagger/Docs: "Authorize" => Bearer <token> -----
security = HTTPBearer(auto_error=True)


# ----- Sesión de BD -----
def get_db() -> Generator[Session, None, None]:
    """Propaga el generator de la capa de datos."""
    yield from get_session()


# ----- Dependencias de usuario actual (desde el token) -----
def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Extrae y valida el token Bearer. Devuelve:
      { "id": <sub:int|str>, "role": <ROLE>, "jti": <str|None> }

    Requisitos:
    - JWT válido (firma/exp/nbf…)
    - type == "access"
    - no revocado (Redis)
    """
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = creds.credentials
    # ---------- DEBUG TEMPORAL (diagnóstico de por qué sale 401) ----------
    try:
        # Si sospechas de reloj/tiempos, puedes subir a 120
        payload = decode_token(token, leeway_seconds=30)
        logger.debug(
            "JWT decodificado OK: sub=%s type=%s jti=%s iss=%s aud=%s",
            payload.get("sub"),
            payload.get("type") or payload.get("typ"),
            payload.get("jti"),
            payload.get("iss"),
            payload.get("aud"),
        )
    except Exception as e:
        logger.warning("JWT inválido (detalle verificación): %s", e)  # <--- QUITAR luego
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    # ---------- FIN DEBUG TEMPORAL ----------

    # Verifica tipo de token (solo 'access' aquí)
    if not validate_token_type(payload, "access"):
        logger.warning(  # <--- QUITAR luego si no quieres logs
            "Token con tipo inesperado: got=%s (esperado=access)",
            payload.get("type") or payload.get("typ"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no válido para acceso (se esperaba 'access')",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Revocación opcional (Redis)
    jti = payload.get("jti")
    if is_revoked(jti):
        logger.warning("Token revocado detectado: jti=%s", jti)  # <--- QUITAR luego
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revocado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # subject obligatorio
    sub = payload.get("sub")
    if sub is None:
        logger.warning("Token sin 'sub' (payload=%s)", payload)  # <--- QUITAR luego
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin 'sub'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # role del token (fallback a OPERARIO)
    role = (payload.get("role") or "OPERARIO").upper()

    # intenta convertir sub a int si procede
    try:
        sub_cast: Any = int(sub)
    except (ValueError, TypeError):
        sub_cast = sub  # mantener como string si no es numérico

    return {"id": sub_cast, "role": role, "jti": jti}


def current_active_user_obj(
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(current_user),
) -> Usuario:
    """
    Carga el objeto Usuario desde BD y verifica que esté activo.
    Útil cuando necesitas el Usuario completo (y no solo id/role del token).
    """
    uid = user.get("id")
    obj = db.get(Usuario, uid)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not obj.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario deshabilitado",
        )
    return obj


# ----- Autorización por rol -----
def require_role(*roles: str, check_db: bool = False) -> Callable:
    """
    Dependencia para proteger endpoints por rol.
    - Si el usuario es ADMIN, pasa siempre.
    - Si se pasan roles, el usuario debe pertenecer a alguno.
    - Si check_db=True, valida contra el rol del Usuario en BD (y que esté activo).
      Si check_db=False (por defecto), usa el rol del token (más rápido).
    """
    roles_up = {r.upper() for r in roles}

    async def dep(
        db: Session = Depends(get_db),
        token_user: Dict[str, Any] = Depends(current_user),
    ):
        # Camino rápido: usamos el rol del token
        if not check_db:
            role = token_user.get("role", "").upper()
            if role == "ADMIN":
                return token_user
            if roles_up and role not in roles_up:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No autorizado",
                )
            return token_user

        # Camino estricto: comprobación en BD y usuario activo
        obj = db.get(Usuario, token_user.get("id"))
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not obj.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario deshabilitado",
            )

        if obj.role.upper() == "ADMIN":
            return {"id": obj.id, "role": obj.role}

        if roles_up and obj.role.upper() not in roles_up:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No autorizado",
            )
        return {"id": obj.id, "role": obj.role}

    return dep
