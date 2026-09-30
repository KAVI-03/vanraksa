import os
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./vanrakshak.db"
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    OWM_API_KEY: str = ""  # OpenWeatherMap — leave blank to use mock data
    USE_POSTGIS: bool = False
    FERNET_KEY: str = Field(min_length=44)  # for encrypting visa_ref
    APP_ENV: str = "development"
    STAFF_USERNAME: str = Field(default="vanrakshak", min_length=1)
    STAFF_PASSWORD: str = Field(default="Vanrakshak@123", min_length=12)

    @field_validator("FERNET_KEY")
    @classmethod
    def validate_fernet_key(cls, value: str) -> str:
        Fernet(value.encode())
        return value

    @model_validator(mode="after")
    def reject_default_staff_credentials_in_production(self):
        if self.APP_ENV.lower() in {"prod", "production"} and (
            self.STAFF_USERNAME == "vanrakshak"
            or self.STAFF_PASSWORD == "Vanrakshak@123"
        ):
            raise ValueError("Production requires unique STAFF_USERNAME and STAFF_PASSWORD values.")
        return self

    class Config:
        env_file = ".env"

settings = Settings()
