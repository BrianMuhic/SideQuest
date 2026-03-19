"""Utilities dealing with strings"""

import re
from string import digits, whitespace
from typing import Any, Iterable


def strip(text: str, characters: str) -> str:
    """Strip characters from text."""
    return text.translate({ord(c): "" for c in characters})


def strip_whitespace(text: str) -> str:
    """Strip whitespace from text."""
    return strip(text, whitespace)


def strip_digits(text: str) -> str:
    """Strip digits from text."""
    return strip(text, digits)


def remove_spaces_after(text: str, string: str) -> str:
    """Remove contiguous spaces after text."""
    return re.sub(text + r"\s+", text, string)


def remove_spaces_before(text: str, string: str) -> str:
    """Remove contiguous spaces before text."""
    return re.sub(r"\s+" + text, text, string)


def as_csv(collection: Iterable[Any]) -> str:
    """Convert an iterable to a comma-separated string."""
    return ",".join(str(item) for item in collection)
