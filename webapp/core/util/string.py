"""Utilities dealing with strings"""

import re
from string import (
    Template,
    digits,
    whitespace,
)


def strip(text: str, characters: str) -> str:
    """Strip whitespace from text"""
    return text.translate({ord(c): "" for c in characters})


def strip_whitespace(text: str) -> str:
    """
    Strip whitespace from text

    >>> strip_whitespace("This is  the forest\tprim")
    'Thisistheforestprim'
    """
    return strip(text, whitespace)


def strip_digits(text: str) -> str:
    """
    Strip digits from text

    >>> strip_digits("/employer2/manual_match/377")
    '/employer/manual_match/'
    """
    return strip(text, digits)


def sub(text: str, target: str, pre: str = " " * 8, post: str = "\n") -> str:
    """
    If target, return text with `$target` replaced with the contents of target

    >>> sub("Replace $target with walrus", "walrus")
    '        Replace walrus with walrus\\n'
    """

    if not target:
        return ""

    text = Template(text).substitute(target=target)
    return f"{pre}{text}{post}"


def remove_spaces_after(text: str, string: str) -> str:
    """Remove contiguous spaces after text"""

    pattern = re.compile(text + r"\s+")
    return pattern.sub(text, string)


def remove_spaces_before(text: str, string: str) -> str:
    """Remove contiguous spaces before text"""

    pattern2 = re.compile(r"\s+" + text)
    return pattern2.sub(text, string)
