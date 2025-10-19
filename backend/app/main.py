from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.logging import setup_logging
from app.core.cors import add_cors
from app.core.db import init_db
from app.core.config import settings

# Logging temprano
setup_logging()

# Ciclo de vida: inicialización al arranque
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    # aquí podrías cerrar pools, caches, etc.

app = FastAPI(
    title="Mantenimiento API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
add_cors(app)

# Routers
from app.auth.routes_auth import router as auth_router
from app.api.v1.routes_equipos import router as equipos_router
from app.api.v1.routes_ubicaciones import router as ubic_router

app.include_router(auth_router, prefix="/api")
app.include_router(equipos_router, prefix="/api/v1")
app.include_router(ubic_router, prefix="/api/v1")

# Healthcheck
@app.get("/health", tags=["_meta"])
def health():
    return {"ok": True, "env": settings.APP_ENV}
