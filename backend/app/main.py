# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.logging import setup_logging
from app.core.cors import add_cors
from app.core.db import init_db
from app.core.config import settings
from app.middleware.security_headers import SecurityHeadersMiddleware

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

# En prod podrías desactivar docs si quieres
docs_url = "/docs"
redoc_url = "/redoc"
openapi_url = "/openapi.json"

app = FastAPI(
    title="Mantenimiento API",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    lifespan=lifespan,
)

# Security headers (pon hsts=True si sirves HTTPS)
app.add_middleware(SecurityHeadersMiddleware, hsts=False)

# Trusted hosts (opcional en prod)
if settings.TRUSTED_HOSTS:
    allowed = [h.strip() for h in settings.TRUSTED_HOSTS.split(",") if h.strip()]
    if allowed:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)

# CORS
add_cors(app)

# Routers
from app.auth.routes_auth import router as auth_router
from app.api.v1.routes_equipos import router as equipos_router
from app.api.v1.routes_ubicaciones import router as ubic_router

app.include_router(auth_router, prefix="/api")
app.include_router(equipos_router, prefix="/api/v1")
app.include_router(ubic_router, prefix="/api/v1")

@app.get("/health", tags=["_meta"])
def health():
    return {"ok": True, "env": settings.APP_ENV}
