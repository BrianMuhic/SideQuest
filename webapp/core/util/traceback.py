"""
Custom traceback formatting for better readability.

This module must have minimal dependencies to ensure it can be imported
at the very top of the application entry point, before any other imports
that might fail.
"""

import sys
from pathlib import Path
from traceback import FrameSummary, extract_tb
from types import TracebackType

_PROJECT_DIR = Path.cwd().name


def exc_info() -> tuple[type[BaseException] | None, BaseException | None, list[FrameSummary]]:
    """
    Get current exception info with extracted traceback.
    Returns exception type, value, and list of FrameSummary objects.
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    return exc_type, exc_value, extract_tb(exc_traceback)


def format_traceback(exc_value: BaseException | None, tb: list[FrameSummary]) -> str:
    """
    Format exception traceback in a structured, readable format.
    Returns formatted string with exception summary and full traceback.

    tb comes from either extract_stack()[:-1] or extract_tb(exc_traceback)
    """
    # Traceback summary
    message = f"{type(exc_value or Exception).__name__}: {exc_value}\n"
    if len(tb) == 0:
        return f"{message}NO TRACEBACK AVAILABLE\n"

    last_frame = tb[-1]

    # Full traceback - Skip frames from frozen/built-in modules with no source
    lines = [
        f"{frame.name:<30}\t{_frame_location(frame):<40}\t'{frame.line}'"
        for frame in tb
        if frame.line and frame.line.strip()
    ]

    message += f"Location: {last_frame.name}, {_frame_location(last_frame)} ({last_frame.colno}:{last_frame.end_colno})\n"
    message += f"Source: {last_frame.line}\n"
    message += f"{'=' * 20} BEGIN TRACEBACK {'=' * 20}\n"
    message += "\n".join(lines)
    message += f"\n{'=' * 21} END TRACEBACK {'=' * 21}"
    return message


def _frame_location(frame: FrameSummary) -> str:
    """Extracts 'file:line' from a FrameSummary."""
    filename = frame.filename
    if "site-packages" in filename:
        filename = filename.split("site-packages", 1)[1]
    elif _PROJECT_DIR in filename:
        filename = filename.split(_PROJECT_DIR, 1)[1]
    return f"{filename}:{frame.lineno}"


def install_custom_excepthook() -> None:
    """
    Install a custom exception handler that formats tracebacks in a readable way.
    This catches startup errors (like circular imports) that occur before Flask error handlers.
    """

    def _custom_excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ):
        """Format uncaught exceptions with structured traceback."""
        if exc_type is KeyboardInterrupt:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        tb = extract_tb(exc_traceback)
        message = f"\n{format_traceback(exc_value, tb)}\n"

        # Use stderr to ensure it's visible
        sys.stderr.write(message)
        sys.stderr.flush()

    sys.excepthook = _custom_excepthook
