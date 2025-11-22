# app/core/rate_limit.py
import time
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


# ===========================
#        LOGIN RATE LIMIT
# ===========================

# --- Claves específicas de login ---
def _key_user_fails(username: str) -> str:
    return f"rl:login:user:{username}:fails"

def _key_ip_fails(ip: str) -> str:
    return f"rl:login:ip:{ip}:fails"

def _key_user_lock(username: str) -> str:
    return f"rl:login:user:{username}:lock"

def _key_ip_lock(ip: str) -> str:
    return f"rl:login:ip:{ip}:lock"


# --- Utilidades TTL ---
def _ttl_seconds(r: redis.Redis, key: str) -> int:
    """
    Devuelve segundos restantes de expiración para 'key'.
    Si no existe o no tiene expiración, devuelve 0.
    """
    ttl = r.ttl(key)
    if ttl is None or ttl < 0:
        return 0
    return int(ttl)


# --- API login ---
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


# ===========================
#   UTILIDADES GENERALES RL
# ===========================

class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int, message: str = "Rate limit exceeded"):
        super().__init__(message)
        self.retry_after = max(1, int(retry_after))


def _now() -> int:
    return int(time.time())


def allow_sliding_window(key: str, limit: int, window_sec: int) -> Tuple[bool, int]:
    """
    Rate limit con ventana deslizante usando Sorted Set en Redis.
    - key: identificador (p.ej. 'nfc-move:u:123' o 'nfc-move:tag:abcd123')
    - limit: nº máx de peticiones por ventana
    - window_sec: tamaño de ventana en segundos

    Devuelve (allowed, retry_after).
    """
    r = get_redis()
    now = _now()
    zkey = f"rl:sw:{key}"

    pipe = r.pipeline()
    # 1) Limpia eventos fuera de la ventana
    pipe.zremrangebyscore(zkey, 0, now - window_sec)
    # 2) Añade evento actual (score=now)
    pipe.zadd(zkey, {str(now): now})
    # 3) Cuenta
    pipe.zcard(zkey)
    # 4) TTL higiene
    pipe.expire(zkey, window_sec + 5)
    _, _, count, _ = pipe.execute()

    if count > limit:
        # Estimación simple del reintento: 1s
        return False, 1
    return True, 0


def set_debounce(key: str, ttl_sec: int) -> bool:
    """
    Debounce anti-doble ejecución inmediata.
    SETNX + TTL: True si pudo fijar (primer intento), False si ya existía.
    """
    r = get_redis()
    dkey = f"deb:{key}"
    ok = r.set(dkey, "1", ex=ttl_sec, nx=True)
    return bool(ok)


def register_idempotency(idem_key: str, ttl_sec: int) -> bool:
    """
    Idempotencia por cabecera X-Idempotency-Key:
    True si se registra (primera vez), False si ya existía (repetida).
    """
    if not idem_key:
        return True
    r = get_redis()
    key = f"idm:{idem_key}"
    ok = r.set(key, "1", ex=ttl_sec, nx=True)
    return bool(ok)
