# app/main.py
import time
import redis
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Final, Dict, Any

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlmodel import Session, select

from app.core.logging import setup_logging, get_logger
from app.core.cors import add_cors
from app.core.db import init_db, get_session
from app.core.config import settings
from app.middleware.security_headers import SecurityHeadersMiddleware

# --- Inicialización de logging ---
setup_logging()
logger = get_logger(__name__)

# --- Metadatos OpenAPI por tags (Swagger) ---
OPENAPI_TAGS: Final = [
    {"name": "equipos", "description": "Gestión de equipos (alta, edición, búsqueda, estadísticas)."},
    {"name": "incidencias", "description": "Alta, edición, cierre y reapertura de incidencias."},
    {"name": "movimientos", "description": "Movimientos entre ubicaciones (retirar/devolver)."},
    {"name": "reparaciones", "description": "Gestión de reparaciones de equipos."},
    {"name": "ubicaciones", "description": "Zonas/almacenes/operarios como ubicaciones lógicas."},
    {"name": "auth", "description": "Autenticación y emisión/refresh de tokens."},
    {"name": "_meta", "description": "Endpoints internos de salud y meta."},
    
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Aplicación iniciada correctamente")
    yield
    logger.info("Aplicación deteniéndose")

# Config de documentación (permite desactivarla por entorno)
docs_url = "/docs" if settings.DOCS_ENABLED else None
redoc_url = "/redoc" if settings.DOCS_ENABLED else None
openapi_url = "/openapi.json" if settings.DOCS_ENABLED else None

app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema de gestión de equipos, mantenimiento, incidencias, movimientos y reparaciones",
    version=settings.VERSION,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
    contact={"name": "Equipo de Mantenimiento", "email": "mantenimiento@empresa.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

# --- Middlewares ---
# Security headers (en prod pon HSTS a True si sirves HTTPS)
app.add_middleware(SecurityHeadersMiddleware, hsts=settings.HSTS_ENABLED)
# GZip (mejora rendimiento en listados)
app.add_middleware(GZipMiddleware, minimum_size=1024)
# Trusted hosts (recomendado en prod)
if settings.trusted_hosts_list:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)
# CORS (expone X-Total-Count y Location desde core/cors.py)
add_cors(app)

# --- Request logging + métrica ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Process-Time-ms"] = str(process_time_ms)

    logger.info(
        f"{request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": process_time_ms,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )
    return response

# ---------- Routers ----------
from app.auth.routes_auth import router as auth_router
from app.api.v1.routes_equipos import router as equipos_router
from app.api.v1.routes_ubicaciones import router as ubic_router
from app.api.v1.routes_incidencias import router as incidencias_router
from app.api.v1.routes_movimientos import router as movimientos_router
from app.api.v1.routes_reparaciones import router as reparaciones_router  # ya integrado
from app.api.v1.routes_secciones import router as secciones_router

# Prefijos coherentes (usa settings.* para no duplicar)
app.include_router(auth_router,        prefix=settings.API_PREFIX,    tags=["auth"])        # /api/auth/...
app.include_router(equipos_router,     prefix=settings.API_V1_PREFIX)                       # /api/v1/equipos
app.include_router(ubic_router,        prefix=settings.API_V1_PREFIX)                       # /api/v1/ubicaciones
app.include_router(incidencias_router, prefix=settings.API_V1_PREFIX)                       # /api/v1/incidencias
app.include_router(movimientos_router, prefix=settings.API_V1_PREFIX)                       # /api/v1/movimientos
app.include_router(reparaciones_router,prefix=settings.API_V1_PREFIX)                       # /api/v1/reparaciones
app.include_router(secciones_router, prefix=settings.API_V1_PREFIX)


# ---------- Endpoints de sistema ----------
@app.get("/", include_in_schema=False, response_class=PlainTextResponse)
def root():
    return "Mantenimiento API - OK"

@app.get("/health", tags=["_meta"])
def health(db: Session = Depends(get_session)):
    try:
        db.exec(select(1))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        logger.error(f"Health check falló: {e}")

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": settings.APP_ENV,
        "database": db_status,
        "version": settings.VERSION,
    }

@app.get("/version", include_in_schema=False)
def version():
    return {
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

@app.get("/_meta/redis", tags=["_meta"])
def redis_health() -> Dict[str, Any]:
    """
    Chequeo básico de Redis (PING) y versión del servidor.
    """
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        pong = r.ping()
        info = r.info(section="server")
        return {
            "ok": bool(pong),
            "redis_version": info.get("redis_version"),
            "mode": info.get("redis_mode"),
            "uptime_in_seconds": info.get("uptime_in_seconds"),
        }
    except Exception as e:
        logger.error(f"Redis health failed: {e}")
        return {"ok": False, "error": str(e)}


# ---------- Manejadores globales de errores ----------
@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError):
    logger.warning(f"IntegrityError: {exc}")
    return JSONResponse(status_code=409, content={"detail": "Conflicto de integridad en base de datos"})

@app.exception_handler(DBAPIError)
async def dbapi_error_handler(_: Request, exc: DBAPIError):
    logger.error(f"DBAPIError: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Error interno de base de datos"})

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        logger.info(f"404 Not Found: {request.method} {request.url.path}")
        return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado"})
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Excepción no manejada: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})
