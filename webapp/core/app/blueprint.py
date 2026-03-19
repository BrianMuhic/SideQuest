import inspect
from os import PathLike
from typing import Any, Callable, Sequence, TypeVar

import flask
from flask.sansio.scaffold import setupmethod

from core.app import endpoint
from core.app.endpoint import Endpoint

T = TypeVar("T", bound=Callable)


class BaseBlueprint(flask.Blueprint):
    """Extended Flask Blueprint with convenient routing utilities."""

    def __init__(
        self,
        name: str,
        import_name: str | None = None,
        url_prefix: str | None = None,
        template_folder: str | PathLike[str] | None = "templates",
        **kwargs,
    ):
        if import_name is None:
            frame = inspect.currentframe()
            if frame and frame.f_back:
                import_name: str = frame.f_back.f_globals.get("__name__")  # type: ignore
            else:
                import_name = "unknown"

        super().__init__(
            name=name,
            import_name=import_name,
            url_prefix=url_prefix,
            template_folder=template_folder,
            **kwargs,
        )

    @setupmethod
    def get_post(self, rule: str, **options: Any) -> Callable[[T], T]:
        """Register a route that responds to GET and POST requests."""
        return self._register_route(["GET", "POST"], rule, **options)

    @setupmethod
    def get(self, rule: str, **options: Any) -> Callable[[T], T]:
        """Register a route that responds to GET requests."""
        return self._register_route(["GET"], rule, **options)

    @setupmethod
    def post(self, rule: str, **options: Any) -> Callable[[T], T]:
        """Register a route that responds to POST requests."""
        return self._register_route(["POST"], rule, **options)

    def _register_route(self, methods: Sequence[str], rule: str, **options) -> Callable[[T], T]:
        """Register a route that responds to <methods> requests."""

        if "methods" in options:
            raise TypeError("Use the 'route' decorator to use the 'methods' argument.")

        def decorator(func: T) -> T:
            self._register_endpoint(func)
            return self.route(rule, methods=methods, **options)(func)

        return decorator

    def _register_endpoint(self, func: Callable):
        """Register route in the endpoint module."""
        name = f"{self.name}_{func.__name__}"  # type: ignore
        ep = Endpoint(func.__name__, self.name)  # type: ignore
        endpoint.add_variable_to_module(name, ep)
