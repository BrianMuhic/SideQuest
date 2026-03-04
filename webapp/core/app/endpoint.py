import sys
from typing import Any

from flask import url_for
from werkzeug import Response
from werkzeug.utils import redirect


class Endpoint:
    """Wrapper for Flask endpoint references with URL generation utilities."""

    def __init__(self, function_name: str, bp_name: str = "webapp") -> None:
        """Initialize an endpoint reference."""
        self.function_name = function_name
        self.bp_name = bp_name

    @property
    def route(self) -> str:
        """Return the fully qualified endpoint name."""
        return f"{self.bp_name}.{self.function_name}"

    def url(self, **kwargs: Any) -> str:
        """Generate a URL for this endpoint."""
        return url_for(self.route, **kwargs)

    def external_url(self, **kwargs: Any) -> str:
        """Generate a URL for this endpoint."""
        from webapp.config import config

        return config.BASE_URL + url_for(self.route, **kwargs)

    def redirect(self, code: int = 302, **kwargs: Any) -> Response:
        """Create a redirect response to this endpoint."""
        return redirect(self.url(**kwargs), code)


def add_variable_to_module(name: str, value: Any) -> None:
    module = sys.modules[__name__]
    setattr(module, name, value)


def __getattr__(name: str) -> Endpoint:
    """Return an Endpoint for any attribute access."""
    if name in globals():
        return globals()[name]
    raise AttributeError(f"module has no attribute '{name}'")
