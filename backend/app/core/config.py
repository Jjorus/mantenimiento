# app/core/config.py
from typing import List, Optional, Literal
from pydantic import AnyHttpUrl, Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    # --- Configuración de carga de entorno (v2) ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "Mantenimiento API"
    APP_ENV: Literal["dev", "staging", "prod", "test"] = "dev"
    VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    DOCS_ENABLED: bool = True

    # Prefijos API
    API_PREFIX: str = "/api"
    API_V1_PREFIX: str = "/api/v1"

    # Paginación
    PAGE_DEFAULT_LIMIT: int = 50
    PAGE_MAX_LIMIT: int = 200

    # --- Seguridad / JWT ---
    SECRET_KEY: SecretStr = Field("dev_change_me_32_chars_min", min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ISSUER: Optional[str] = "http://localhost"
    AUDIENCE: Optional[str] = "mant-client"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOTP_ISSUER: str = "EmpresaMant"

    # --- Base de datos ---
    DATABASE_URL: str = "postgresql+psycopg://dev:devpass@localhost:5432/mant_dev"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = Field(5, ge=1)
    DB_MAX_OVERFLOW: int = Field(10, ge=0)
    DB_POOL_RECYCLE: int = Field(3600, ge=0)
    DB_POOL_TIMEOUT: int = Field(30, ge=1)

    # --- Redis / Cache ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- CORS ---
    CORS_ALLOWED_ORIGINS: List[AnyHttpUrl] = Field(
        default_factory=lambda: ["http://localhost", "http://127.0.0.1:3000", "http://localhost:5173"]
    )
    CORS_ALLOWED_ORIGINS_RAW: Optional[str] = Field(default=None)
    ALLOW_ORIGINS_REGEX: Optional[str] = None
    CORS_EXPOSE_HEADERS: List[str] = Field(
        default_factory=lambda: ["X-Total-Count", "Location"]
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"])

    # --- Trusted hosts (prod) ---
    TRUSTED_HOSTS: Optional[str] = None

    # --- Rate Limiting / Anti brute-force ---
    RATE_LIMIT_GLOBAL: str = "200/minute"
    LOGIN_MAX_FAILS_PER_USER: int = 8
    LOGIN_BLOCK_TTL_PER_USER_SECONDS: int = 900
    LOGIN_MAX_FAILS_PER_IP: int = 30
    LOGIN_BLOCK_TTL_PER_IP_SECONDS: int = 900

    # --- SSL/TLS (producción) ---
    FORCE_HTTPS: bool = False
    HSTS_ENABLED: bool = False
    HSTS_MAX_AGE: int = 31536000

    # --- Timeouts ---
    REQUEST_TIMEOUT: int = 30
    KEEP_ALIVE: int = 5

    # --- Ficheros / almacenamiento ---
    # Directorio base donde se guardan las facturas subidas (PDF/JPG/etc.).
    # Se puede sobrescribir vía env: FACTURAS_DIR=/ruta/que/quieras
    FACTURAS_DIR: str = "data/facturas"

    @model_validator(mode="after")
    def _apply_cors_from_raw(self):
        raw = self.CORS_ALLOWED_ORIGINS_RAW
        if not raw:
            return self
        s = raw.strip()
        try:
            if s.startswith("["):                 # formato JSON
                self.CORS_ALLOWED_ORIGINS = json.loads(s)
            else:                                 # CSV
                self.CORS_ALLOWED_ORIGINS = [x.strip() for x in s.split(",") if x.strip()]
        except (json.JSONDecodeError, ValidationError):
            # Si falla, deja el default y no rompas la carga
            pass
        return self

    # ------- Propiedades útiles -------

    @property
    def cors_allowed_origins_as_str(self) -> List[str]:
        """Convierte AnyHttpUrl -> str para Starlette CORSMiddleware."""
        return [str(o) for o in self.CORS_ALLOWED_ORIGINS]

    @property
    def trusted_hosts_list(self) -> List[str]:
        """Devuelve la lista de hosts confiables para TrustedHostMiddleware."""
        if not self.TRUSTED_HOSTS:
            return []
        return [h.strip() for h in self.TRUSTED_HOSTS.split(",") if h.strip()]

    @property
    def BACKEND_CORS_ORIGINS(self) -> str:
        """CSV con orígenes CORS permitido (backwards compatibility)."""
        return ",".join(self.cors_allowed_origins_as_str)

    @property
    def is_development(self) -> bool:
        """Verifica si el entorno es desarrollo."""
        return self.APP_ENV == "dev"

    @property
    def is_production(self) -> bool:
        """Verifica si el entorno es producción."""
        return self.APP_ENV == "prod"

    @property
    def is_staging(self) -> bool:
        """Verifica si el entorno es staging."""
        return self.APP_ENV == "staging"

    @property
    def should_use_https(self) -> bool:
        """Determina si se debe forzar HTTPS."""
        return self.is_production or self.FORCE_HTTPS

    @property
    def is_testing(self) -> bool:
        """Verifica si el entorno es testing."""
        return self.APP_ENV == "test"


settings = Settings()
