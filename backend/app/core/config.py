from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HUSTUDY_",
        env_file=".env",
        extra="ignore",
        hide_input_in_errors=True,
    )
    env: str = "development"
    speech_model_path: str = Field(
        default="./data/models/faster-whisper-base", max_length=1024, repr=False
    )
    database_url: str = "sqlite:///./data/hustudy.db"
    storage_root: str = "./data/storage"
    worker_autostart: bool | None = None
    storage_reserve_bytes: int = Field(default=64 * 1024 * 1024, ge=1024 * 1024)
    libreoffice_path: str = Field(default="", max_length=1024, repr=False)
    jwt_secret: str = Field(default="", min_length=32, repr=False)
    access_token_minutes: int = 120
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    llm_provider: Literal["mock", "zhipu", "compatible"] = "mock"
    llm_model: str = Field(default="glm-5.3-flash", min_length=1, max_length=128)
    llm_endpoint: str = (
        "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    )
    zhipu_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    credential_account_id: str | None = Field(default=None, repr=False)
    credential_revision: int = 0
    credential_scope: str = "active"
    llm_vendor: str = "zhipu"
    llm_vision: bool = True
    llm_thinking: bool = False
    llm_json_mode: bool = True
    additional_ai_hosts: str = ""

    @property
    def manage_worker(self) -> bool:
        return (
            self.worker_autostart
            if self.worker_autostart is not None
            else self.env == "development"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def base_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    from .connection_store import apply

    return apply(base_settings())


get_settings.cache_clear = base_settings.cache_clear


def get_user_settings(user_id: str) -> Settings:
    from .account_connection import effective
    from .model_connections import apply

    return apply(effective(base_settings(), user_id), user_id)


def get_zhipu_settings(user_id: str) -> Settings:
    from .account_connection import effective

    return effective(base_settings(), user_id).model_copy(update={"credential_scope": "zhipu"})
