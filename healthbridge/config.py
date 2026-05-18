from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the HealthBridge application.

    Reads configuration from environment variables and an optional .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Garmin Connect Credentials
    garmin_email: str | None = Field(
        default=None,
        description="The email address associated with your Garmin Connect account.",
        validation_alias="GARMIN_EMAIL",
    )

    garmin_password: SecretStr | None = Field(
        default=None,
        description="The password associated with your Garmin Connect account.",
        validation_alias="GARMIN_PASSWORD",
    )

    garmin_is_cn: bool = Field(
        default=False,
        description="Whether to use the Garmin Connect China server.",
        validation_alias="GARMIN_IS_CN",
    )

    garmin_token_path: Path = Field(
        default=Path(".garminconnect"),
        description="Directory path where tokens are stored to persist sessions.",
        validation_alias="GARMIN_TOKEN_PATH",
    )

    @property
    def has_credentials(self) -> bool:
        """Helper property to check if email and password are provided."""
        return bool(self.garmin_email and self.garmin_password)


@lru_cache
def get_settings() -> Settings:
    """Helper function to load and cache the application settings."""
    return Settings()
