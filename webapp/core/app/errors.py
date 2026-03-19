from http import HTTPStatus

from flask import Flask, redirect, request
from flask.templating import render_template
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import (
    HTTPException,
    Unauthorized,
)

from core.service.logger import get_logger
from core.util.traceback import exc_info, format_traceback

log = get_logger()

IGNORE_404 = {
    "/ads.txt",
    "/apple-touch-icon-precomposed.png",
    "/.well-known/appspecific/com.chrome.devtools.json",
}


def register_error_handlers(app: Flask) -> None:
    app.register_error_handler(HTTPException, handle_http_exception)
    app.register_error_handler(Exception, handle_exception)


# ==================== Exception Handlers ==================== #


def handle_http_exception(err: HTTPException) -> ResponseReturnValue:
    """Handle general http exceptions and return appropriate details."""

    if not err.description or err.code in (None, HTTPStatus.INTERNAL_SERVER_ERROR):
        return handle_exception(err)

    # Redirect unauthenticated users to login page
    if isinstance(err, Unauthorized) and request.method == "GET":
        return redirect("/", code=302)

    if err.code != HTTPStatus.NOT_FOUND or request.path not in IGNORE_404:
        message = f"{err.code} {err.name} on {request.method} {request.path}"
        if err.description != getattr(type(err), "description", None):
            message += f": {err.description}"
        log.w(message)

    return render_error(err.name, err.description, err.code)


def handle_exception(_err: Exception) -> ResponseReturnValue:
    """Log the error (to file and email)."""
    log_traceback()
    return render_error(
        name="Internal Server Error",
        description="Oops, you have encountered an unexpected error. We have logged this issue and will be work to resolve it quickly.",
        code=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


# ==================== Helpers ==================== #


def render_error(name: str, description: str, code: int) -> ResponseReturnValue:
    if request.method == "POST" or request.content_type == "application/json":
        return description, code
    response = render_template(
        "simple.html",
        title=name,
        content=description,
    )
    return response, code


def log_traceback(postscript: str = "") -> None:
    """Log the current exception with traceback and request context."""

    exc_type, exc_value, tb = exc_info()
    message = f"{(exc_type or Exception).__name__} on {request.method} {request.path}: {exc_value}"
    trace = format_traceback(exc_value, tb)
    if postscript:
        log.e(f"{message}\n{trace}\n{postscript}")
    else:
        log.e(f"{message}\n{trace}")
