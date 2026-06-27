from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    database_url_sync: str = ""
    jwt_secret: str
    jwt_expire_hours: int = 24
    google_ai_api_key: str = ""
    cloudflare_account_id: str = ""
    cloudflare_r2_access_key_id: str = ""
    cloudflare_r2_secret_key: str = ""
    r2_bucket_name: str = "jobai-raw"
    r2_public_url: str = ""
    resend_api_key: str = ""
    from_email: str = "noreply@example.com"
    sentry_dsn_api: str = ""


settings = Settings()
