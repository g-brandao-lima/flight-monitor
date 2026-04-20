from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./flight_monitor.db"
    serpapi_api_key: str = ""
    gmail_sender: str = ""
    gmail_app_password: str = ""
    gmail_recipient: str = ""
    app_base_url: str = "http://localhost:8000"
    google_client_id: str = ""
    google_client_secret: str = ""
    session_secret_key: str = "dev-secret-change-in-production"
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1
    admin_email: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
