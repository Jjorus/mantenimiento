# app/core/rate_limit.py
import redis
from typing import Tuple, Optional
from app.core.config import settings

# ---------------------------
# Cliente Redis (lazy singleton)
# ---------------------------
_redis_client: Optional[redis.Redis] = None

def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        # decode_responses=True -> strings en vez de bytes
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


# ---------------------------
# Claves
# ---------------------------
def _key_user_fails(username: str) -> str:
    return f"rl:login:user:{username}:fails"

def _key_ip_fails(ip: str) -> str:
    return f"rl:login:ip:{ip}:fails"

def _key_user_lock(username: str) -> str:
    return f"rl:login:user:{username}:lock"

def _key_ip_lock(ip: str) -> str:
    return f"rl:login:ip:{ip}:lock"


# ---------------------------
# Utilidades TTL
# ---------------------------
def _ttl_seconds(r: redis.Redis, key: str) -> int:
    """
    Devuelve segundos restantes de expiración para 'key'.
    Si no existe o no tiene expiración, devuelve 0.
    """
    ttl = r.ttl(key)
    if ttl is None or ttl < 0:
        return 0
    return int(ttl)


# ---------------------------
# API pública
# ---------------------------
def is_locked(username: str, ip: str) -> Tuple[bool, int, str]:
    """
    True si hay lock activo por usuario o por IP.
    Devuelve (locked, ttl_restante, motivo: 'user'|'ip'|'').
    """
    r = get_redis()
    u_key = _key_user_lock(username)
    i_key = _key_ip_lock(ip)

    u_ttl = _ttl_seconds(r, u_key)
    if u_ttl > 0:
        return True, u_ttl, "user"

    i_ttl = _ttl_seconds(r, i_key)
    if i_ttl > 0:
        return True, i_ttl, "ip"

    return False, 0, ""


def incr_login_fail(username: str, ip: str) -> Tuple[int, int]:
    """
    Incrementa contadores de fallo y aplica TTL deslizante.
    NO pone el lock (eso lo hace lock_if_needed()).
    Devuelve (u_count, i_count).
    """
    r = get_redis()

    u_key = _key_user_fails(username)
    i_key = _key_ip_fails(ip)

    u_count = r.incr(u_key)
    r.expire(u_key, settings.LOGIN_BLOCK_TTL_PER_USER_SECONDS)

    i_count = r.incr(i_key)
    r.expire(i_key, settings.LOGIN_BLOCK_TTL_PER_IP_SECONDS)

    return int(u_count), int(i_count)


def lock_if_needed(username: str, ip: str) -> Tuple[bool, int, str]:
    """
    Si los contadores han alcanzado el umbral, crea el lock correspondiente.
    Devuelve (locked, ttl, motivo).
    """
    r = get_redis()

    u_count = int(r.get(_key_user_fails(username)) or 0)
    i_count = int(r.get(_key_ip_fails(ip)) or 0)

    if u_count >= settings.LOGIN_MAX_FAILS_PER_USER:
        # Lock de usuario
        r.set(_key_user_lock(username), "1", ex=settings.LOGIN_BLOCK_TTL_PER_USER_SECONDS, nx=True)
        ttl = _ttl_seconds(r, _key_user_lock(username))
        return True, ttl, "user"

    if i_count >= settings.LOGIN_MAX_FAILS_PER_IP:
        # Lock de IP
        r.set(_key_ip_lock(ip), "1", ex=settings.LOGIN_BLOCK_TTL_PER_IP_SECONDS, nx=True)
        ttl = _ttl_seconds(r, _key_ip_lock(ip))
        return True, ttl, "ip"

    return False, 0, ""


def reset_login_counters_and_unlock(username: str, ip: str) -> None:
    """
    En login exitoso: elimina contadores y locks.
    """
    r = get_redis()
    r.delete(
        _key_user_fails(username),
        _key_ip_fails(ip),
        _key_user_lock(username),
        _key_ip_lock(ip),
    )
