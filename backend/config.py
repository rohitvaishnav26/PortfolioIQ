from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ibkr_host: str = "127.0.0.1"
    ibkr_tws_port: int = 4002
    ibkr_client_id: int = 1
    ibkr_account: str = ""
    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./portfolioiq.db"
    app_env: str = "development"
    log_level: str = "INFO"
    sync_interval_minutes: int = 5
    quote_refresh_seconds: int = 60
    ohlcv_cache_ttl_hours: int = 24
    fundamental_cache_ttl_hours: int = 6
    research_cache_ttl_hours: int = 24
    research_daily_call_limit: int = 20
    research_model: str = "claude-opus-4-5"
    signal_model: str = "claude-sonnet-4-5"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
