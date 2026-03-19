#!/usr/bin/env python

"""
Wrapper for logging

Use cases:
  print: should not be in production code.  Convert to one of the following...
  echo : Used to communicate with the (CLI) user.  Should be pretty (colorful) and non-technical.
  log.d:  Inform developer of the flow of a program.  Normally only seen in optional log file.
  log.i:  Inform developer that an important event has occurred.  Normally will be displayed in stderr.
  log.w:  Inform developer that an abnormal event has occurred, but is being handled.
  log.e:  Inform developer that an operation has failed but the system can still function.
  log.c:  Inform developer of a fatal event that needs to be handled ASAP.

Note: logger will capture exceptions if you do something like this...
    from lib.config import log

    try:
        typer_run(main)
    except Exception as e:
        log.exception(f"{sys.argv[0]} Exception")
"""

import inspect
import logging
from datetime import datetime
from logging import (
    FileHandler,
    Logger,
    LogRecord,
    StreamHandler,
)
from logging.handlers import SMTPHandler
from pathlib import Path
from typing import Any, ClassVar, cast

from flask import has_request_context
from flask_login import current_user


class CustomLogger(Logger):
    def d(self, msg, *args, **kwargs) -> None:
        pass

    def i(self, msg, *args, **kwargs) -> None:
        pass

    def w(self, msg, *args, **kwargs) -> None:
        pass

    def e(self, msg, *args, **kwargs) -> None:
        pass

    def c(self, msg, *args, **kwargs) -> None:
        pass

    @staticmethod
    def wrap(logger: logging.Logger) -> "CustomLogger":
        """Add abbreviations to logger methods"""
        setattr(logger, "d", logger.debug)
        setattr(logger, "i", logger.info)
        setattr(logger, "w", logger.warning)
        setattr(logger, "e", logger.error)
        setattr(logger, "c", logger.critical)

        return cast(CustomLogger, logger)


class CustomFormatter(logging.Formatter):
    LOG_FORMAT: ClassVar[str] = (
        "{asctime} " + "{levelname} " + "{user_id:<6} " + "{location:<34} " + "| {message} "
    )
    DATE_FORMAT: ClassVar[str] = "%m/%d %H:%M:%S"
    STRIP_PREFIXES: ClassVar[list[str]] = [
        "webapp.",
    ]

    def __init__(self):
        super().__init__(self.LOG_FORMAT, self.DATE_FORMAT, style="{")

    def formatTime(self, record: LogRecord, datefmt: str | None = None) -> str:  # noqa: N802
        from webapp.constant import LOCAL_ZONEINFO

        dt = datetime.fromtimestamp(record.created, tz=LOCAL_ZONEINFO)

        # Get timezone offset in hours (-4 or -5)
        utc_offset = dt.utcoffset()
        tz_offset_seconds = utc_offset.total_seconds() if utc_offset is not None else 0
        tz_offset_hours = int(tz_offset_seconds / 3600)

        formatted_time = dt.strftime(datefmt or self.DATE_FORMAT)
        return f"{formatted_time}.{record.msecs:03.0f}{tz_offset_hours:+d}"

    def format(self, record: LogRecord) -> str:
        # User ID
        record.user_id = ""
        if has_request_context() and getattr(current_user, "is_authenticated", False):
            if user_id := getattr(current_user, "id", ""):
                record.user_id = f"u{user_id}"

        # Location
        name = record.name
        for prefix in self.STRIP_PREFIXES:
            if name.startswith(prefix):
                name = record.name[len(prefix) :]
        if len(name) > 30:
            name = record.name[-30:]
        record.location = f"{name}:{record.lineno:<3d}"

        # Level name
        record.levelname = record.levelname[:4]

        return super().format(record)


class CustomFilter(logging.Filter):
    """Filter out log messages that match any string in the FILTER_MESSAGES list"""

    FILTER_MESSAGES: ClassVar[set[str]] = {
        "Connection reset by peer",
        "* Debugger is active",
    }

    def filter(self, record: LogRecord) -> bool:
        """
        Return False if the log message contains any of the filter strings
        """
        message = record.getMessage()
        return not any(filter_msg in message for filter_msg in self.FILTER_MESSAGES)


class SFLSMTPHandler(SMTPHandler):
    def getSubject(self, record: LogRecord) -> str:  # noqa: N802
        return record.message.split("\n")[0]


def _add_handler(
    logger: logging.Logger,
    level: int | str,
    handler: logging.Handler,
) -> None:
    """Add handler for level to logger with formatter and filters"""
    handler.setLevel(level)
    handler.setFormatter(CustomFormatter())
    handler.addFilter(CustomFilter())
    logger.addHandler(handler)


def make_logger(
    logger: logging.Logger | None = None,  # Used to reuse logger.
    # Streams
    streams_level: int | str | None = logging.DEBUG,
    # File
    file_level: int | str | None = logging.DEBUG,
    log_filename: str | None = None,
    # Email
    mail_level: int | str | None = None,
    mail_host: str = "localhost",
    mail_port: int = 25,
    credentials: tuple[str, str] | None = None,
    secure: None = None,  # we do not use
    timeout: float = 2.0,
    from_addr: str = "local",
    to_addrs: str | list[str] = "",
    subject: str = "Logger Error",
) -> CustomLogger:
    """
    Return a customized logger that will log to stderr, and
    log to a rotating file if log_filename is provided, and
    log to a email if to_addrs is provided, and

    If logger is None, the root logger will be modified.

    By default, log.i, log.e, log.w and log.c will go to stderr,
    while log.d will also go to file.
    """

    logger = logger or logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    if streams_level:
        handler = StreamHandler()
        _add_handler(logger, streams_level, handler)

    if file_level and log_filename:
        Path(log_filename).parent.mkdir(parents=True, exist_ok=True)
        handler = FileHandler(log_filename, encoding="utf8")
        _add_handler(logger, file_level, handler)

    if mail_level and to_addrs:
        handler = SFLSMTPHandler(
            (mail_host, mail_port),
            from_addr,
            to_addrs,
            subject,
            credentials,
            secure,
            timeout,
        )
        _add_handler(logger, mail_level, handler)

    return CustomLogger.wrap(logger)


def config_logger(config_: Any) -> None:
    """Calls make_logger with arguments from config"""

    make_logger(
        logger=None,
        streams_level=config_.LOG_STREAMS_LEVEL or None,
        file_level=config_.LOG_FILE_LEVEL or None,
        mail_level=config_.LOG_MAIL_LEVEL or None,
        log_filename=config_.LOG_FILE,
        mail_host=config_.MAIL_SERVER,
        mail_port=config_.LOG_MAIL_PORT,
        credentials=(config_.MAIL_USERNAME, config_.MAIL_PASSWORD),
        from_addr=config_.LOG_MAIL_SENDER,
        to_addrs=config_.LOG_MAIL_RECIPIENTS,
        subject="Logger Error",
    )


def set_log_level(level: int | str, *logger_names: str) -> None:
    for name in logger_names:
        logging.getLogger(name).setLevel(level)


def get_logger(name: str | None = None) -> CustomLogger:
    """Return the logger for `name` or inspect the frame to get the name (module) automatically. Wrap it with abbreviations."""
    if name is None:
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get("__name__")
    logger = logging.getLogger(name)
    return CustomLogger.wrap(logger)
