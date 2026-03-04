import time
from functools import wraps
from typing import Any, TypeVar

from typing_extensions import Callable, Self

from core.service.logger import get_logger

log = get_logger()


T = TypeVar("T", bound=Callable[..., Any])


def with_timer(func: T) -> T:
    @wraps(func)  # This preserves the original function's metadata
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with Timer(func.__name__):
            return func(*args, **kwargs)

    return wrapper  # type: ignore


class Timer:
    def __init__(self, name: str | None = None) -> None:
        self.name = name
        self.start = self.end = self.dt = 0.0

    def __enter__(self) -> Self:
        log.d(f"{'start':7} \t {self.name}")
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        if self.name:
            log.i(str(self))

    def __str__(self) -> str:
        self.end = time.perf_counter()
        self.dt = self.end - self.start
        return f"{self.dt:7.2f}s\t✓{self.name}"
