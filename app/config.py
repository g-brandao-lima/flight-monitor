from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./flight_monitor.db"
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    gmail_sender: str = ""
    gmail_app_password: str = ""
    gmail_recipient: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
