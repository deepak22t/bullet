from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Story Analyzer"
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")

    # LLM
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", validation_alias="OPENAI_BASE_URL")
    llm_model: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL")
    # Google Generative Language API (Gemini). Use env file — never commit keys.
    google_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    )
    google_genai_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        validation_alias="GOOGLE_GENAI_BASE_URL",
    )
    gemini_model: str = Field(default="gemini-2.0-flash", validation_alias="GEMINI_MODEL")
    # Which remote provider to use when keys exist: auto|openai|google
    llm_provider: str = Field(default="auto", validation_alias="LLM_PROVIDER")
    # mock = instant deterministic output for demos/CI; live = call provider when key present
    analysis_mode: str = Field(default="auto", validation_alias="ANALYSIS_MODE")  # auto|live|mock

    http_timeout_seconds: float = Field(default=45.0, validation_alias="HTTP_TIMEOUT_SECONDS")
    max_concurrent_llm_calls: int = Field(default=3, validation_alias="MAX_CONCURRENT_LLM_CALLS")

    title_max_chars: int = 200
    scene_max_chars: int = 8000
    dialogue_max_chars: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
