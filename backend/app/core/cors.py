from starlette.middleware.cors import CORSMiddleware
from app.core.config import settings

def add_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.CORS_ALLOWED_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET","POST","PATCH","DELETE"],
        allow_headers=["authorization","content-type"]
    )
