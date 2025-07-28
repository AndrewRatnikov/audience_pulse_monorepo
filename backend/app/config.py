
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost"]
    YOUTUBE_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
