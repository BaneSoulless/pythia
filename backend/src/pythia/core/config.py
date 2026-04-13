"""
Live-Fire Configuration
SOTA 2026 - Pydantic V2 Compatible

Loads secrets from .env using pydantic-settings.
Enforces SECRET_KEY rotation in non-development environments.
"""

import logging
import secrets

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_INSECURE_DEFAULT = "default-secret-key-change-me"


class Settings(BaseSettings):
    """Application settings with security enforcement."""

    PROJECT_NAME: str = "AI-Trading-Bot"
    VERSION: str = "4.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    SECRET_KEY: str = _INSECURE_DEFAULT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql://pythia:pythia_password@localhost:5432/pythia_db"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    MIN_BALANCE: float = 1000.0
    MAX_POSITION_SIZE: float = 5000.0
    RISK_PER_TRADE: float = 0.02

    EXCHANGE_ID: str = "binance"
    EXCHANGE_API_KEY: str = ""
    EXCHANGE_SECRET_KEY: str = ""
    EXCHANGE_TESTNET: bool = True

    OPENAI_API_KEY: str | None = None
    CORS_ORIGINS: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: list[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and (not v.startswith("[")):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    @model_validator(mode="after")
    def enforce_secret_key_security(self) -> "Settings":
        """Fail-fast if default SECRET_KEY is used in production."""
        if self.SECRET_KEY == _INSECURE_DEFAULT:
            if self.ENVIRONMENT in ("production", "staging"):
                raise ValueError(
                    "CRITICAL: SECRET_KEY must be rotated before deployment. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(64))\""
                )
            logger.warning(
                "SECRET_KEY is set to the insecure default. "
                "This is acceptable in development only. "
                "Set SECRET_KEY env var before deploying."
            )
        if len(self.SECRET_KEY) < 32:
            generated = secrets.token_hex(64)
            logger.warning(
                "SECRET_KEY too short (<%d chars). Auto-generating secure key.",
                32,
            )
            self.SECRET_KEY = generated
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
