from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "FastAPI Application"
    admin_email: Optional[str] = None
    database_url: str = "sqlite:///./test.db"
    secret_key: str = "your-secret-key-here"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    class Config:
        env_file = ".env"

settings = Settings()