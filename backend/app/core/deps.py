# app/core/deps.py
from typing import Generator, Any, Dict, Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session
from app.core.security import decode_token  # <--- centralizamos validación JWT
from app.models.usuario import Usuario

# ----- Seguridad para Swagger/Docs: "Authorize" => Bearer <token> -----
# auto_error=True => FastAPI devolverá 403 si falta Authorization; nosotros
# igualmente enriquecemos los mensajes cuando hay token pero es inválido.
security = HTTPBearer(auto_error=True)

# ----- Sesión de BD -----
def get_db() -> Generator[Session, None, None]:
    yield from get_session()

# ----- Revocación opcional de tokens vía Redis (si está disponible) -----
_redis_client = None  # lazy init

def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis  # type: ignore
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        _redis_client = None  # Redis no disponible; seguimos sin revocación
    return _redis_client

def _is_token_revoked(jti: Optional[str]) -> bool:
    if not jti:
        return False
    r = _get_redis()
    if not r:
        return False
    try:
        return r.exists(f"jwt:revoked:{jti}") == 1
    except Exception:
        # Si Redis falla, no bloqueamos por revocación
        return False

# ----- Dependencias de usuario actual (desde el token) -----
def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Extrae y valida el token Bearer. Devuelve un dict mínimo con:
      { "id": <sub:int|str>, "role": <ROLE>, "jti": <id del token o None> }

    Requisitos:
    - Debe ser un token de tipo ACCESS (acepta claim 'typ' o 'type' == 'access').
    - Respeta verificación condicional de ISS/AUD (config en settings).
    - Aplica revocación opcional por Redis si 'jti' está presente.
    """
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = creds.credentials
    try:
        payload = decode_token(token, leeway_seconds=30)  # tolerancia de reloj
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer error='invalid_token'"},
        )

    # tipo de token: aceptamos 'typ' o 'type'
    ttype = (payload.get("typ") or payload.get("type") or "access").lower()
    if ttype != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no válido para acceso (se esperaba 'access')",
            headers={"WWW-Authenticate": "Bearer error='invalid_token'"},
        )

    # subject (usuario) obligatorio
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin 'sub'",
            headers={"WWW-Authenticate": "Bearer error='invalid_token'"},
        )

    # rol del token (fallback a OPERARIO)
    role = (payload.get("role") or "OPERARIO").upper()

    # revocación opcional (si hay jti)
    jti = payload.get("jti")
    if _is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revocado",
            headers={"WWW-Authenticate": "Bearer error='invalid_token'"},
        )

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

        # check_db=True: comprobación en BD y usuario activo
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
