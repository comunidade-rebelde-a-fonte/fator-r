from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida do ambiente. Nenhum segredo tem valor padrão real."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Padrão seguro: sem ENV explícito, comporta-se como produção (cookie Secure, sem rotas de dev).
    env: Literal["dev", "test", "prod"] = "prod"
    # Role da aplicação (sujeita a RLS). A role dona só é usada por migrações e seed.
    database_url: str = "postgresql+asyncpg://fator_r_app:change-me@localhost:5432/fator_r"
    database_owner_url: str | None = None
    upload_dir: str = "/data/uploads"
    upload_max_mb: int = 10
    cors_origins: list[str] = ["http://localhost:3000"]

    session_cookie_name: str = "fr_session"
    session_ttl_hours: int = 12
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 900

    # Langfuse self-hosted (CLAUDE.md §5.3: nunca Langfuse Cloud)
    langfuse_tracing_enabled: bool = True
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "http://localhost:3100"
    langfuse_public_url: str = "http://localhost:3100"
    langfuse_project_id: str = "fator-r-dev"
    langfuse_export_timeout_s: int = 5
    trace_payload_max_kb: int = 32
    langfuse_sync_interval_s: int = 30
    rotina_priorizador_hora: int = 7

    # Claude: só intenção (plan) e redação (render). "fake" é permitido só em dev/test (E2E).
    llm_provider: Literal["anthropic", "fake"] = "anthropic"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    @property
    def owner_database_url(self) -> str:
        return self.database_owner_url or self.database_url

    @property
    def cookie_secure(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
