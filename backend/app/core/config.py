# app/core/config.py
from typing import List, Optional
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
    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # --- Seguridad / JWT ---
    SECRET_KEY: SecretStr = Field("dev_change_me_32_chars_min", min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ISSUER: Optional[str] = "http://localhost"     # déjalo None si no verificas 'iss'
    AUDIENCE: Optional[str] = "mant-client"        # déjalo None si no verificas 'aud'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOTP_ISSUER: str = "EmpresaMant"

    # --- Base de datos ---
    DATABASE_URL: str = "postgresql+psycopg://dev:devpass@localhost:5432/mant_dev"
    DB_ECHO: bool = False

    # --- Redis / Cache ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- CORS ---
    # Usa default_factory para que Pydantic parsee strings -> AnyHttpUrl
    CORS_ALLOWED_ORIGINS: List[AnyHttpUrl] = Field(
        default_factory=lambda: ["http://localhost", "http://127.0.0.1:3000"]
    )

    # 2) Campo "raw" que mapea a la MISMA env, pero como string (evita parseo JSON previo)
    CORS_ALLOWED_ORIGINS_RAW: Optional[str] = Field(
        default=None
       
    )

    @model_validator(mode="after")
    def _apply_cors_from_raw(self):
        raw = self.CORS_ALLOWED_ORIGINS_RAW
        if not raw:
            return self
        s = raw.strip()
        try:
            if s.startswith("["):                 # JSON
                self.CORS_ALLOWED_ORIGINS = json.loads(s)
            else:                                 # CSV
                self.CORS_ALLOWED_ORIGINS = [x.strip() for x in s.split(",") if x.strip()]
        except (json.JSONDecodeError, ValidationError):
            # Si falla, deja el default y no rompas la carga
            pass
        return self


    # --- Rate Limiting ---
    RATE_LIMIT_GLOBAL: str = "200/minute"

settings = Settings()
