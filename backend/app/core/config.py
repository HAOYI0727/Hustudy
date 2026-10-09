from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HUSTUDY_", env_file=".env", extra="ignore")
    env: str = "development"
    database_url: str = "sqlite:///./data/hustudy.db"
    storage_root: str = "./data/storage"
    jwt_secret: str = "change-this-in-development"
    access_token_minutes: int = 120
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
@lru_cache
def get_settings() -> Settings:
    return Settings()
