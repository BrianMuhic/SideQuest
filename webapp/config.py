"""
This file contains the app's configuration variables.
Secrets and server-dependent info should be in .env
"""

import logging
from pathlib import Path
from typing import Sequence

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REQ = "(Replace Me)"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    IS_PRODUCTION: bool = False
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 5000
    APP_URL: str = f"http://{APP_HOST}:{APP_PORT}"
    SECRET_KEY: str = _REQ
    USER_SESSION_TIMEOUT_MINUTES: int = 60

    # Testing
    DEBUG: bool = True
    TESTING: bool = False
    WTF_CSRF_ENABLED: bool = True

    # Database
    DB_DATABASE: str = "sidequest"
    DB_HOST: str = "localhost"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_PORT: int = 3306
    DB_DIALECT: str = "mysql"
    DB_DRIVER: str = "pymysql"
    DB_EXTRAS: str | None = None

    # DB Session Timer
    DB_TIME_WARN_THRESHOLD: float = 2.0
    DB_TIME_ERROR_THRESHOLD: float = 4.0
    DB_TIME_IGNORE: Sequence[str] = ()

    # Formats
    DATE_FORMAT: str = "%m/%d/%y"
    DATE_LONG_FORMAT: str = "%B %-d, %Y"
    DATETIME_FORMAT: str = "%m/%d/%Y %I:%M %p"
    LOCAL_TIMEZONE: str = "America/New_York"

    # Logger
    LOG_STREAMS_LEVEL: int | str | None = logging.DEBUG
    LOG_FILE_LEVEL: int | str | None = logging.DEBUG
    LOG_MAIL_LEVEL: int | str | None = logging.ERROR
    LOG_FILE: Path | str | None = None
    LOG_MAIL_SENDER: str = _REQ
    LOG_MAIL_RECIPIENTS: Sequence[str] = ()
    LOG_MAIL_PORT: int = 25

    # Mail
    # DO NOT SET TO False EXCEPT FOR IN PRODUCTION ENV
    MAIL_REDIRECT_TO_DEVELOPER: bool = True
    MAIL_DEFAULT_SENDER: str = _REQ
    MAIL_USERNAME: str = _REQ
    MAIL_PASSWORD: str = _REQ
    MAIL_SERVER: str = "smtp.mailgun.org"
    MAIL_PORT: int = 465
    MAIL_USE_TLS: bool = False
    MAIL_USE_SSL: bool = True

    # Computed
    @computed_field
    def DB_CONNECTION_STRING(self) -> str:  # noqa: N802
        if self.TESTING:
            return "sqlite:///:memory:"
        return f"{self.DB_DIALECT}+{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}{self.DB_EXTRAS}"


config = Settings()
