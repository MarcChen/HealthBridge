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
        populate_by_name=True,
    )

    # Garmin Connect Token configuration
    garmin_token: SecretStr | None = Field(
        default=None,
        description="The Garmin Connect OAuth/session token JSON content.",
        validation_alias="GARMIN_TOKEN",
    )

    garmin_email: SecretStr | None = Field(
        default=None,
        description="The Garmin Connect email address.",
        validation_alias="GARMIN_EMAIL",
    )

    garmin_username: SecretStr | None = Field(
        default=None,
        description="Alternative name for Garmin Connect email.",
        validation_alias="GARMIN_USERNAME",
    )

    garmin_password: SecretStr | None = Field(
        default=None,
        description="The Garmin Connect password.",
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
    def email_or_username(self) -> str:
        """Helper to get either email or username as string."""
        if self.garmin_email:
            return self.garmin_email.get_secret_value()
        if self.garmin_username:
            return self.garmin_username.get_secret_value()
        return ""

    @property
    def password_str(self) -> str:
        """Helper to get password as string."""
        if self.garmin_password:
            return self.garmin_password.get_secret_value()
        return ""

    @property
    def has_token(self) -> bool:
        """Helper property to check if a session token is provided."""
        return bool(self.garmin_token)

    @property
    def has_credentials(self) -> bool:
        """Check if email/username and password are configured."""
        return bool(self.email_or_username and self.password_str)

    @property
    def has_auth(self) -> bool:
        """Check if we have at least some authentication configuration."""
        return self.has_token or self.has_credentials


@lru_cache
def get_settings() -> Settings:
    """Helper function to load and cache the application settings."""
    return Settings()
