from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    web_origin: str = "http://localhost:3000"
    detect_backend: str = "vlm"
    gemini_api_key: str = ""
    gemini_model: str = ""
    catalog_path: str = "../data/catalog/appliance_catalog.csv"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("supabase_url")
    @classmethod
    def normalize_supabase_project_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return value

        parsed = urlsplit(value)
        if parsed.path in {"/rest/v1", "/rest/v1/"}:
            parsed = parsed._replace(path="")
            return urlunsplit(parsed).rstrip("/")
        if parsed.path not in {"", "/"}:
            raise ValueError(
                "SUPABASE_URL must be the project URL, without a path such as /rest/v1"
            )
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
