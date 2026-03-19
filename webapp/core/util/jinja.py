"""Utilities dealing with strings containing jinja expressions"""

import re

from core.util.string import remove_spaces_after, remove_spaces_before


def find_variables(string: str) -> list[str]:
    """Return a list of variables in a string where a variable is wrapped in two braces."""

    return [s.strip() for s in re.findall(r"\{\{([^}]+)\}\}", string)]


def wrap_variables(string: str, before: str, after: str) -> str:
    """Return a string where all variables are wrapped with before and after."""

    variables = find_variables(string)
    open_braces = "{{"
    close_braces = "}}"
    for variable in variables:
        target = f"{open_braces}{variable}{close_braces}"
        string = string.replace(target, f"{before}{target}{after}")
    return string


def remove_spaces_around_variables(string: str | None) -> str | None:
    """Remove spaces from variables."""
    if string is None:
        return None

    string = remove_spaces_after("{{", string)
    string = remove_spaces_before("}}", string)
    return string
