# app/core/security.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

from jose import jwt, JWTError
from passlib.hash import argon2

from app.core.config import settings

# ===========================
#   HASHING DE CONTRASEÑAS
# ===========================
# Parámetros razonables para Argon2id (puedes exponerlos en settings si lo deseas)
# time_cost=3  -> iteraciones de cómputo
# memory_cost  -> KB (64*1024 = 64 MB)
# parallelism=2
_pwd_hasher = argon2.using(type="ID", time_cost=3, memory_cost=64 * 1024, parallelism=2)

def hash_password(password: str) -> str:
    return _pwd_hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    # passlib ya maneja timing-safe comparators
    return _pwd_hasher.verify(password, password_hash)


# ===========================
#       UTILIDADES JWT
# ===========================
def _now() -> datetime:
    return datetime.now(timezone.utc)

def _jwt_key() -> str:
    # SECRET_KEY es SecretStr en settings
    return settings.SECRET_KEY.get_secret_value()

def _jwt_alg() -> str:
    return getattr(settings, "JWT_ALGORITHM", "HS256") or "HS256"

def _std_claims(sub: str, role: str, exp_delta: timedelta, token_type: str) -> Dict[str, Any]:
    now = _now()
    exp = now + exp_delta
    claims: Dict[str, Any] = {
        "sub": str(sub),
        "role": str(role).upper(),
        "typ": token_type,          # "access" | "refresh"
        "iat": int(now.timestamp()),
        "nbf": int((now - timedelta(seconds=5)).timestamp()),  # pequeña holgura de reloj
        "exp": int(exp.timestamp()),
    }
    # Solo forzamos verificación si están definidos
    if settings.ISSUER:
        claims["iss"] = settings.ISSUER
    if settings.AUDIENCE:
        claims["aud"] = settings.AUDIENCE
    return claims

def make_jwt(
    sub: str,
    role: str,
    *,
    token_type: str = "access",
    expires_delta: Optional[timedelta] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Genera un JWT genérico (access/refresh).
    - token_type: "access" (por defecto) o "refresh"
    - expires_delta: duración (por defecto: settings.ACCESS_TOKEN_EXPIRE_MINUTES o REFRESH_TOKEN_EXPIRE_DAYS)
    - extra: claims adicionales
    """
    if token_type not in {"access", "refresh"}:
        raise ValueError("token_type debe ser 'access' o 'refresh'")

    if expires_delta is None:
        if token_type == "access":
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        else:
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = _std_claims(sub, role, exp_delta=expires_delta, token_type=token_type)
    if extra:
        payload.update(extra)

    return jwt.encode(payload, _jwt_key(), algorithm=_jwt_alg())

def make_access_token(sub: str, role: str, extra: Optional[Dict[str, Any]] = None) -> str:
    return make_jwt(sub, role, token_type="access", extra=extra)

def make_refresh_token(sub: str, role: str, extra: Optional[Dict[str, Any]] = None) -> str:
    return make_jwt(sub, role, token_type="refresh", extra=extra)

def issue_token_pair(sub: str, role: str) -> Dict[str, str]:
    """
    Genera un par (access, refresh) coherente.
    """
    return {
        "access_token": make_access_token(sub, role),
        "refresh_token": make_refresh_token(sub, role),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # segundos
    }

# ===========================
#       DECODIFICACIÓN
# ===========================
def decode_token(token: str, *, leeway_seconds: int = 10) -> Dict[str, Any]:
    """
    Decodifica/valida un JWT. Respeta ISSUER/AUDIENCE si están configurados.
    - leeway_seconds: tolerancia de reloj
    """
    key = _jwt_key()
    algorithms = [_jwt_alg()]
    options: Dict[str, Any] = {}

    kwargs: Dict[str, Any] = {"algorithms": algorithms, "options": options, "leeway": leeway_seconds}

    if settings.ISSUER:
        kwargs["issuer"] = settings.ISSUER
    if settings.AUDIENCE:
        kwargs["audience"] = settings.AUDIENCE
    else:
        # Si no definimos AUDIENCE, desactiva verificación de 'aud'
        options["verify_aud"] = False

    return jwt.decode(token, key, **kwargs)

def try_decode_token(token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Variante que NO lanza excepción: devuelve (payload|None, error|None)
    """
    try:
        return decode_token(token), None
    except JWTError as e:
        return None, str(e)


__all__ = [
    # password hashing
    "hash_password",
    "verify_password",
    # jwt issuing
    "make_jwt",
    "make_access_token",
    "make_refresh_token",
    "issue_token_pair",
    # jwt decoding
    "decode_token",
    "try_decode_token",
]
