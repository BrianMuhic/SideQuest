from typing import Literal

from wtforms import Field, Form
from wtforms.validators import Regexp

# ==================== Constants ==================== #

POSTAL_REGEX = Regexp(r"^$|^\d{5}(?:-\d{4})?$")
INT_POSTAL_REGEX = Regexp(r"^$|^[^\W_]{5}(?:-[^\W_]{4})?$")  # International
PHONE_REGEX = Regexp(r"^$|^(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$")
WEB_REGEX = Regexp(r"^((https?|ftp|smtp):\/\/)?(www.)?[a-z0-9]+\.[a-z]+(\/[a-zA-Z0-9#]+\/?)*$")

validation_attrs = [
    "required",
    "disabled",
    "readonly",
    "maxlength",
    "minlength",
    "pattern",
]

readonly_attrs = {
    "readonly": "readonly",
    "disabled": True,
    "class": "read_only_field",
}
readonly_no_disable_attrs = {"class": "read_only_field", "readonly": "readonly"}
hidden_attrs = {"style": "display: none;", "type": "hidden", "class": "hidden"}


# ==================== Validators ==================== #


class AppearRequired:
    def __init__(self) -> None:
        self.field_flags = {"appear_required": True}

    def __call__(self, form: Form, field: Field) -> None:
        pass


# ==================== Filters ==================== #


def str_strip(value: str | None) -> str | None:
    """Filter to strip leading and trailing whitespace from a StringField."""
    return value.strip() if value else None


def str_lower(value: str | None) -> str | None:
    """Filter to force a string to lowercase from a StringField."""
    return value.lower() if value else None


# ==================== Helpers ==================== #


def add_error(field: Field, message: str) -> Literal[False]:
    field.errors.append(message)  # type: ignore
    return False
