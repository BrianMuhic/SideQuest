"""
This file contains the app's configuration variables.
Secrets and server-dependent info should be in .env
"""

from os import getenv
from typing import Sequence

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

_REQ = "(Replace Me)"


class Settings(BaseSettings):
    APP_NAME: str = "Flask Template"
    IS_PRODUCTION: bool = False

    # Testing
    DEBUG: bool = True
    TESTING: bool = False
    WTF_CSRF_ENABLED: bool = True

    FLASK_RUN_HOST: str = "127.0.0.1"
    FLASK_RUN_PORT: int = 5000
    BASE_URL: str = f"http://{FLASK_RUN_HOST}:{FLASK_RUN_PORT}"

    # Forms
    SECRET_KEY: str = _REQ
    USER_SESSION_TIMEOUT_MINUTES: int = 60

    # Database
    ENGINE_DATABASE: str = "sidequest"
    ENGINE_HOST: str = "localhost"
    ENGINE_USER: str = "root"
    ENGINE_PASSWORD: str = ""
    ENGINE_PORT: int = 3306
    ENGINE_DIALECT: str = "mysql"
    ENGINE_DRIVER: str = "pymysql"
    ENGINE_EXTRAS: str = ""
    CONNECTION_STRING: str | None = None

    # DB Session Timer
    DB_SESSION_TIME_WARN_THRESHOLD: float = 1.0
    DB_SESSION_TIME_ERROR_THRESHOLD: float = 3.0
    DB_SESSION_TIME_IGNORE: Sequence[str] = ()

    # Formats
    DATE_FORMAT: str = "%m/%d/%y"
    DATE_LONG_FORMAT: str = "%B %-d, %Y"
    DATETIME_FORMAT_LONG: str = "%m/%d/%Y %I:%M %p"
    LOCAL_TIMEZONE: str = "America/New_York"

    # Logger
    LOG_STREAMS_LEVEL: str = "DEBUG"
    LOG_FILE_LEVEL: str | None = None
    LOG_FILE_NAME: str = ""
    LOG_EMAIL_LEVEL: str | None = None
    LOG_MAIL_FROM: str = _REQ
    LOG_MAIL_TO: Sequence[str] = ()
    LOG_MAIL_PORT: int = 25

    # Mail
    # DO NOT SET TO False EXCEPT FOR IN PRODUCTION .env
    MAIL_REDIRECT_TO_DEVELOPER: bool = True
    MAIL_USERNAME: str = _REQ
    MAIL_PASSWORD: str = _REQ
    MAIL_SENDER: str = _REQ
    MAIL_SERVER: str = "smtp.mailgun.org"
    MAIL_PORT: int = 465
    MAIL_USE_TLS: bool = False
    MAIL_USE_SSL: bool = True

    # reCAPTCHA
    RECAPTCHA_SITE_KEY: str = _REQ
    RECAPTCHA_SECRET_KEY: str = _REQ

    # Password
    PASSWORD_MIN_LENGTH: int = 6
    PASSWORD_MIN_UPPERCASE: int = 1
    PASSWORD_MIN_NUMBERS: int = 1
    PASSWORD_MIN_SPECIAL: int = 1


load_dotenv(getenv(".env"), override=True)
config = Settings()
