# app/core/cors.py
from starlette.middleware.cors import CORSMiddleware
from app.core.config import settings


def add_cors(app) -> None:
    """
    Monta CORSMiddleware usando los valores tipados de settings.
    - Soporta orígenes desde CSV/JSON vía CORS_ALLOWED_ORIGINS_RAW.
    - Expone X-Total-Count y Location (usados por listados/creaciones).
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins_as_str,
        allow_origin_regex=settings.ALLOW_ORIGINS_REGEX,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=settings.CORS_EXPOSE_HEADERS,
    )
