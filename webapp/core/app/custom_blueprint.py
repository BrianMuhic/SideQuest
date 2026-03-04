from functools import partial
from os import PathLike
from typing import Any, Callable

from flask import (
    Blueprint,
    redirect,
    url_for,
)
from flask.sansio.scaffold import setupmethod
from werkzeug.wrappers import Response as BaseResponse

from core.app import endpoint
from core.app.endpoint import Endpoint

type RouteType = Callable | str | Endpoint


class CustomBlueprint(Blueprint):
    """Extended Flask Blueprint with convenient routing utilities."""

    def __init__(
        self,
        name: str,
        import_name: str,
        template_folder: str | PathLike[str] | None = "templates",
        static_folder: str | PathLike[str] | None = None,
        static_url_path: str | None = None,
        url_prefix: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            name=name,
            import_name=import_name,
            static_folder=static_folder,
            static_url_path=static_url_path,
            template_folder=template_folder,
            url_prefix=url_prefix,
            **kwargs,
        )

    def __call__(self, route: RouteType) -> str:
        """Convert a route to a fully qualified endpoint name."""
        if isinstance(route, Endpoint):
            return route.route
        endpoint = route if isinstance(route, str) else route.__name__
        return f"{self.name}.{endpoint}"

    def url_for(self, route: RouteType, **kwargs: Any) -> str:
        """Generate a URL for the given route."""
        return url_for(self(route), **kwargs)

    def redirect(self, route: RouteType, code: int = 302, **kwargs: Any) -> BaseResponse:
        """Create a redirect response to the given route."""
        url = self.url_for(route, **kwargs)
        return redirect(url, code)

    def partial_url_for(self, route: RouteType, **kwargs: Any) -> Callable:
        """Allow controller to pass url_for with route and some arguments to template"""
        return partial(url_for, self(route), **kwargs)

    @setupmethod
    def get_post(self, rule: str, **options: Any) -> Callable:
        """Same as @bp.route(<RULE>, methods=["GET", "POST"])"""
        if "methods" in options:
            raise TypeError("Use the 'route' decorator to use the 'methods' argument.")

        def decorator(func: Callable) -> Callable:
            self._auto_register_endpoint(func)
            decorated_func = self.route(rule, methods=["GET", "POST"], **options)(func)
            return decorated_func

        return decorator

    @setupmethod
    def get(self, rule: str, **options: Any) -> Callable:
        """Register a route that responds to GET requests."""
        if "methods" in options:
            raise TypeError("Use the 'route' decorator to use the 'methods' argument.")

        def decorator(func: Callable) -> Callable:
            self._auto_register_endpoint(func)
            decorated_func = self.route(rule, methods=["GET"], **options)(func)
            return decorated_func

        return decorator

    @setupmethod
    def post(self, rule: str, **options: Any) -> Callable:
        """Register a route that responds to POST requests."""
        if "methods" in options:
            raise TypeError("Use the 'route' decorator to use the 'methods' argument.")

        def decorator(func: Callable) -> Callable:
            self._auto_register_endpoint(func)
            decorated_func = self.route(rule, methods=["POST"], **options)(func)
            return decorated_func

        return decorator

    def _auto_register_endpoint(self, func: Callable) -> None:
        """Automatically register endpoint in endpoint.py module."""
        name = f"{self.name}_{func.__name__}"
        ep = Endpoint(func.__name__, self.name)
        endpoint.add_variable_to_module(name, ep)
