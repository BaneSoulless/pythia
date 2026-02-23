"""
Live-Fire Configuration
SOTA 2026 - Pydantic V2 Compatible

Loads secrets from .env using pydantic-settings.
"""
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = 'AI-Trading-Bot'
    VERSION: str = '2026.1.0-LIVE'
    API_V1_STR: str = '/api/v1'
    ENVIRONMENT: str = 'development'
    DEBUG: bool = False
    SECRET_KEY: str = 'default-secret-key-change-me'
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    DATABASE_URL: str = 'sqlite:///./backend/app.db'
    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    EXCHANGE_ID: str = 'binance'
    EXCHANGE_API_KEY: str = ''
    EXCHANGE_SECRET_KEY: str = ''
    EXCHANGE_TESTNET: bool = True
    OPENAI_API_KEY: Optional[str] = None
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and (not v.startswith('[')):
            return [i.strip() for i in v.split(',')]
        elif isinstance(v, list):
            return v
        return []
    model_config = {'env_file': '.env', 'env_file_encoding': 'utf-8', 'extra': 'ignore'}
settings = Settings()