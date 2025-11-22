# backend/app/auth/routes_auth.py
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from jose import jwt, JWTError

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import (
    verify_password,
    issue_token_pair,
    revoke_token_by_payload,
    is_revoked,
    decode_token,
    validate_token_type,
    try_decode_token,
)
from app.core.rate_limit import (
    is_locked as rl_is_locked,
    incr_login_fail as rl_incr_fail,
    lock_if_needed as rl_lock_if_needed,
    reset_login_counters_and_unlock as rl_reset_ok,
)
from app.models.usuario import Usuario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
# auto_error=False para poder decidir en cada endpoint si el Bearer es opcional u obligatorio
bearer = HTTPBearer(auto_error=False)


# ---------------------------
# Schemas
# ---------------------------
class LoginIn(BaseModel):
    username_or_email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshOut(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None  # devolvemos refresh rotado
    token_type: str = "bearer"
    expires_in: int


class LogoutIn(BaseModel):
    refresh_token: Optional[str] = None


# ---------------------------
# Utilidades
# ---------------------------
def _db_user_by_username_or_email(db: Session, username_or_email: str) -> Optional[Usuario]:
    key = (username_or_email or "").strip()
    # Con CITEXT en username/email, la comparación ya es case-insensitive.
    stmt = select(Usuario).where((Usuario.email == key) | (Usuario.username == key)).limit(1)
    return db.exec(stmt).first()


def _client_ip(req: Request) -> str:
    # Respeta proxy inverso si existe
    xfwd = req.headers.get("x-forwarded-for")
    if xfwd:
        # Toma el primer IP de la lista
        ip = xfwd.split(",")[0].strip()
        if ip:
            return ip
    xreal = req.headers.get("x-real-ip")
    if xreal:
        return xreal.strip()
    return req.client.host if req.client else "unknown"


def _decode_unverified(token: str) -> Dict[str, Any]:
    """Lee claims sin validar firma (solo como último recurso en logout)."""
    try:
        return jwt.get_unverified_claims(token)
    except Exception:
        return {}


def _ttl_for_token_claims(claims: Dict[str, Any]) -> int:
    """TTL restante a partir de 'exp' (con margen)."""
    exp = claims.get("exp")
    if not exp:
        return 3600  # 1 hora por defecto
    now = int(datetime.now(timezone.utc).timestamp())
    remaining = max(0, exp - now)
    return remaining + 60  # margen de 60s


def _norm_login_key(v: str) -> str:
    """Normaliza clave usada en rate-limit (user/ip)."""
    return (v or "").strip().lower()


def _auth_401(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------
# Endpoints
# ---------------------------
@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, req: Request, resp: Response, db: Session = Depends(get_db)) -> TokenOut:
    ip = _client_ip(req)
    user_key = _norm_login_key(payload.username_or_email)

    # Verificar bloqueo por rate limiting
    locked, ttl, _ = rl_is_locked(user_key, ip)
    if locked:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos. Intente en {ttl}s",
        )

    # Buscar usuario y verificar credenciales
    user = _db_user_by_username_or_email(db, payload.username_or_email)
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        rl_incr_fail(user_key, ip)
        rl_lock_if_needed(user_key, ip)
        raise _auth_401("Credenciales inválidas")

    # Login exitoso
    rl_reset_ok(user_key, ip)
    access_token, refresh_token, _, _ = issue_token_pair(user.id, user.role)

    logger.info(
        "Login exitoso",
        extra={"event": "auth_login_ok", "user_id": user.id, "username": user.username, "ip": ip},
    )

    # No cachear respuesta con tokens
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Pragma"] = "no-cache"

    return TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60,
    )


@router.post("/refresh", response_model=RefreshOut)
def refresh_token(resp: Response, creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> RefreshOut:
    """
    Renueva access token usando refresh token (en Authorization: Bearer).
    Rotación de refresh:
      - Revoca el refresh usado (con TTL restante)
      - Devuelve nuevo par (access + refresh)
    """
    if not creds or not creds.credentials:
        raise _auth_401("Falta token en Authorization")

    token = creds.credentials

    try:
        claims = decode_token(token, leeway_seconds=30)  # valida firma/exp/iss/aud
    except JWTError as e:
        logger.warning("Refresh token inválido: %s", e, extra={"event": "auth_refresh_fail"})
        raise _auth_401("Refresh token inválido")

    if not validate_token_type(claims, "refresh"):
        logger.warning("Token no es de tipo refresh", extra={"event": "auth_refresh_wrong_type"})
        raise _auth_401("Token no es de tipo refresh")

    jti = claims.get("jti")
    if is_revoked(jti):
        logger.warning("Refresh token revocado", extra={"event": "auth_refresh_revoked"})
        raise _auth_401("Refresh token revocado")

    sub = claims.get("sub")
    role = claims.get("role", "OPERARIO")
    if not sub:
        raise _auth_401("Token sin subject")

    # Rotación: revocar el refresh usado (con TTL derivado de exp)
    revoke_token_by_payload(claims)

    # Emitir nuevo par
    new_access_token, new_refresh_token, _, _ = issue_token_pair(sub, role)
    logger.info("Tokens refrescados", extra={"event": "auth_refresh_ok", "sub": sub, "role": role})

    # No cachear respuesta con tokens
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Pragma"] = "no-cache"

    return RefreshOut(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60,
    )


@router.post("/logout")
def logout(
    payload: LogoutIn = LogoutIn(),  # body opcional
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),  # Bearer opcional
):
    """
    Revoca el access token actual (Authorization: Bearer)
    y opcionalmente un refresh token pasado en el body.
    Si no se proporciona ninguno, 400.
    """
    revoked_count = 0

    if (not creds or not creds.credentials) and not payload.refresh_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Proporcione Authorization Bearer y/o refresh_token")

    # Revocar access token del header
    if creds and creds.credentials:
        # Intentar validar; si falla (expirado), usar unverified claims para revocarlo igual
        try:
            access_claims = decode_token(creds.credentials, leeway_seconds=30)
        except JWTError:
            access_claims = _decode_unverified(creds.credentials)

        if access_claims.get("jti"):
            # Es válido revocar aunque no sea 'access', pero lo normal es ACCESS aquí
            revoke_token_by_payload(access_claims)
            revoked_count += 1
            logger.info("Access token revocado", extra={"event": "auth_logout_access", "jti": access_claims.get("jti")})

    # Revocar refresh token del body (si se proporciona)
    if payload.refresh_token:
        try:
            refresh_claims = decode_token(payload.refresh_token, leeway_seconds=30)
        except JWTError:
            refresh_claims = _decode_unverified(payload.refresh_token)

        if refresh_claims.get("jti"):
            revoke_token_by_payload(refresh_claims)
            revoked_count += 1
            logger.info("Refresh token revocado", extra={"event": "auth_logout_refresh", "jti": refresh_claims.get("jti")})

    return {"detail": "Sesión cerrada", "tokens_revocados": revoked_count}


@router.post("/logout-all")
def logout_all(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
):
    """
    Logout global - revoca el token actual y prepara el terreno para revocar todos.
    Nota: para revocar *todos* los tokens de un usuario de forma efectiva
    habría que mantener un set de JTI por usuario en Redis (pendiente de implementar).
    """
    if not creds or not creds.credentials:
        raise _auth_401("Falta token en Authorization")

    token = creds.credentials
    try:
        claims = decode_token(token, leeway_seconds=30)
    except JWTError:
        raise _auth_401("Token inválido")

    user_id = claims.get("sub")
    if not user_id:
        raise _auth_401("Token sin subject")

    user = db.get(Usuario, int(user_id))
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Revocamos, al menos, el token actual
    revoke_token_by_payload(claims)
    logger.info("Logout global iniciado", extra={"event": "auth_logout_all", "user_id": user_id})

    return {
        "detail": "Logout global iniciado",
        "user_id": user_id,
        "mensaje": "Token actual revocado. Para revocar todos los tokens activos, implementa tracking de JTI por usuario.",
    }


@router.post("/debug/decode")
def debug_decode(token: str):
    payload, err = try_decode_token(token, leeway_seconds=120)
    if err:
        return {"ok": False, "error": err}
    return {"ok": True, "payload": payload}
