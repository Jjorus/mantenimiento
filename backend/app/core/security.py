# app/core/security.py
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any, Union

from jose import jwt, JWTError
from passlib.hash import argon2

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------
# Password hashing (Argon2id)
# ---------------------------
_pwd_hasher = argon2.using(type="ID", time_cost=3, memory_cost=64 * 1024, parallelism=2)

def hash_password(plain: str) -> str:
    """Hash seguro de contraseñas usando Argon2id."""
    return _pwd_hasher.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash."""
    try:
        return _pwd_hasher.verify(plain, hashed)
    except Exception as e:
        logger.warning("Error verificando password hash: %s", e)
        return False


# ---------------------------
# Utilidades comunes
# ---------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)

def _gen_jti() -> str:
    return uuid.uuid4().hex

def _get_secret_key() -> str:
    sk = settings.SECRET_KEY
    return sk.get_secret_value() if hasattr(sk, "get_secret_value") else str(sk)

def _get_algorithm() -> str:
    return getattr(settings, "JWT_ALGORITHM", "HS256") or "HS256"


# ---------------------------
# Claims & emisión de tokens
# ---------------------------
def _base_claims(
    sub: Union[str, int],
    role: str,
    token_type: str,              # "access" | "refresh"
    exp_delta: timedelta,
    jti: Optional[str] = None,
) -> Dict[str, Any]:
    iat = _now()
    claims: Dict[str, Any] = {
        "sub": str(sub),
        "role": str(role).upper(),
        "type": token_type,                       # <- clave compatible con deps.current_user
        "iat": int(iat.timestamp()),
        "nbf": int(iat.timestamp()),
        "exp": int((iat + exp_delta).timestamp()),
        "jti": jti or _gen_jti(),
    }
    if settings.ISSUER:
        claims["iss"] = settings.ISSUER
    if settings.AUDIENCE:
        claims["aud"] = settings.AUDIENCE
    return claims

def _encode(claims: Dict[str, Any]) -> str:
    return jwt.encode(claims, _get_secret_key(), algorithm=_get_algorithm())

def issue_access_token(sub: Union[str, int], role: str, jti: Optional[str] = None) -> Tuple[str, str]:
    """Emite un token de acceso y devuelve (token, jti)."""
    minutes = int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    claims = _base_claims(sub, role, "access", timedelta(minutes=minutes), jti=jti)
    token = _encode(claims)
    logger.debug("Access token emitido para sub=%s", sub)
    return token, claims["jti"]

def issue_refresh_token(sub: Union[str, int], role: str, jti: Optional[str] = None) -> Tuple[str, str]:
    """Emite un token de refresh y devuelve (token, jti)."""
    days = int(getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7))
    claims = _base_claims(sub, role, "refresh", timedelta(days=days), jti=jti)
    token = _encode(claims)
    logger.debug("Refresh token emitido para sub=%s", sub)
    return token, claims["jti"]

def issue_token_pair(sub: Union[str, int], role: str) -> Tuple[str, str, str, str]:
    """Devuelve (access_token, refresh_token, access_jti, refresh_jti)."""
    access_token, jti_access = issue_access_token(sub, role)
    refresh_token, jti_refresh = issue_refresh_token(sub, role)
    return access_token, refresh_token, jti_access, jti_refresh


# ---------------------------
# Decodificación / validación
# ---------------------------
def decode_token(token: str, leeway_seconds: int = 10) -> Dict[str, Any]:
    """
    Decodifica y valida un JWT. Verifica iss/aud solo si están configurados.
    Usa 'options' para pasar 'leeway' (python-jose no admite kw 'leeway').
    Lanza JWTError si es inválido.
    """
    options = {
        "verify_aud": bool(settings.AUDIENCE),
        "verify_iss": bool(settings.ISSUER),
        "leeway": leeway_seconds,   # <-- aquí va el leeway
    }

    kwargs: Dict[str, Any] = {
        "key": _get_secret_key(),
        "algorithms": [_get_algorithm()],
        "options": options,
    }
    if settings.ISSUER:
        kwargs["issuer"] = settings.ISSUER
    if settings.AUDIENCE:
        kwargs["audience"] = settings.AUDIENCE

    try:
        payload = jwt.decode(token, **kwargs)
        logger.debug(
            "Token decodificado. sub=%s type=%s",
            payload.get("sub"),
            payload.get("type") or payload.get("typ"),
        )
        return payload
    except JWTError as e:
        logger.warning("Error decodificando token: %s", e)
        raise

def try_decode_token(token: str, leeway_seconds: int = 10) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Devuelve (payload, error_message) sin lanzar excepción."""
    try:
        return decode_token(token, leeway_seconds), None
    except JWTError as e:
        return None, str(e)


# ---------------------------
# Revocación de tokens (Redis)
# ---------------------------
_redis_client = None  # lazy singleton

def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis  # type: ignore
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Cliente Redis inicializado para revocación de tokens")
    except Exception as e:
        logger.warning("Redis no disponible para revocación de tokens: %s", e)
        _redis_client = None
    return _redis_client

def revoke_token(jti: str, ttl_seconds: Optional[int] = None) -> bool:
    """
    Marca un token como revocado. Si no se especifica TTL, se usa 24h como fallback.
    Preferible usar 'revoke_token_by_payload' cuando se disponga de 'exp'.
    """
    if not jti:
        logger.warning("Intento de revocar token sin JTI")
        return False
    r = _get_redis()
    if not r:
        logger.warning("Redis no disponible, no se puede revocar token")
        return False
    try:
        r.setex(f"jwt:revoked:{jti}", ttl_seconds if (ttl_seconds and ttl_seconds > 0) else 86400, "1")
        logger.info("Token revocado: %s (ttl=%s)", jti, ttl_seconds)
        return True
    except Exception as e:
        logger.error("Error revocando token %s en Redis: %s", jti, e)
        return False

def revoke_token_by_payload(payload: Dict[str, Any]) -> bool:
    """
    Revoca un token usando su payload (calcula TTL en base a 'exp' si existe).
    """
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti:
        return False

    ttl_seconds = None
    if exp:
        now_ts = int(_now().timestamp())
        remaining = max(0, int(exp) - now_ts)
        if remaining > 0:
            ttl_seconds = remaining + 60  # margen de seguridad

    return revoke_token(jti, ttl_seconds)

def is_revoked(jti: Optional[str]) -> bool:
    """
    True si el token está revocado. Si Redis no está disponible, devuelve False.
    """
    if not jti:
        return False
    r = _get_redis()
    if not r:
        return False
    try:
        return r.exists(f"jwt:revoked:{jti}") == 1
    except Exception as e:
        logger.error("Error consultando revocación de %s: %s", jti, e)
        return False

def revoke_all_user_tokens(user_id: Union[str, int]) -> int:
    """
    Logout global del usuario. (Stub: requiere llevar tracking de JTI por usuario).
    Devuelve el número de tokens revocados (0 en esta implementación).
    """
    logger.info("Logout global solicitado para user_id=%s (stub)", user_id)
    return 0


# ---------------------------
# Utilidades de seguridad
# ---------------------------
def validate_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
    """
    Valida que el tipo de token sea el esperado. Acepta 'type' y 'typ' por compatibilidad.
    """
    token_type = payload.get("type") or payload.get("typ")
    if not token_type:
        return False
    return str(token_type).lower() == str(expected_type).lower()

def get_token_remaining_ttl(payload: Dict[str, Any]) -> int:
    """
    Segundos restantes de vida del token (0 si ya expiró o no hay 'exp').
    """
    exp = payload.get("exp")
    if not exp:
        return 0
    return max(0, int(exp) - int(_now().timestamp()))


# ---------------------------
# NFC Security Helpers
# ---------------------------

from fastapi import Request, HTTPException, status

def assert_idempotent(request: Request, ttl_sec: int = 30) -> None:
    """
    Verifica idempotencia basada en Idempotency-Key.
    Acepta 'X-Idempotency-Key' o 'Idempotency-Key'.
    Si Redis falla, no bloquea la solicitud.
    """
    try:
        idem_key = request.headers.get("X-Idempotency-Key") or request.headers.get("Idempotency-Key")
        if not idem_key:
            return  # sin header => no aplicamos

        r = _get_redis()
        if not r:
            return  # sin Redis => no aplicamos

        key = f"idempotency:{idem_key}"
        # NX + TTL: si ya existe, es repetida
        ok = r.set(key, "1", nx=True, ex=ttl_sec)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solicitud duplicada (Idempotency-Key ya usado dentro del TTL)",
            )
    except HTTPException:
        raise
    except Exception:
        # Falla Redis u otro: no tiramos la solicitud por robustez
        return


def assert_debounce(key_suffix: str, ttl_sec: int = 3) -> None:
    """
    Previene ejecuciones demasiado frecuentes de la misma acción (debounce).
    Si Redis no está disponible o falla, no interrumpe la solicitud.
    """
    try:
        r = _get_redis()
        if not r:
            return
        key = f"debounce:{key_suffix}"
        # Si existe, estamos en ventana de debounce
        if r.exists(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiadas solicitudes en poco tiempo",
            )
        r.setex(key, ttl_sec, "1")
    except HTTPException:
        raise
    except Exception:
        return



def check_rate_limit_nfc(user_id: str, nfc_tag: str, limit: int = 5, window_sec: int = 10) -> None:
    """
    Rate limiting específico para operaciones NFC por (user_id, nfc_tag).
    Si Redis no está disponible o falla, no interrumpe la solicitud.
    """
    try:
        r = _get_redis()
        if not r:
            return

        key = f"rate_limit:nfc:{user_id}:{(nfc_tag or '').strip().lower()}"
        current = int(r.get(key) or 0)

        if current >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Límite de operaciones NFC excedido",
            )

        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_sec)
        pipe.execute()
    except HTTPException:
        raise
    except Exception:
        return


# ---------------------------
# Exports
# ---------------------------
__all__ = [
    # Password hashing
    "hash_password",
    "verify_password",

    # Token issuance
    "issue_access_token",
    "issue_refresh_token",
    "issue_token_pair",

    # Token decoding
    "decode_token",
    "try_decode_token",

    # Token revocation
    "revoke_token",
    "revoke_token_by_payload",
    "is_revoked",
    "revoke_all_user_tokens",

    # Utilities
    "validate_token_type",
    "get_token_remaining_ttl",

    # NFC Security helpers
    "assert_idempotent",
    "assert_debounce", 
    "check_rate_limit_nfc",

]
