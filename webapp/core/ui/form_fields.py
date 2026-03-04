import datetime
from typing import Any

import requests
from flask import current_app, request
from markupsafe import Markup
from wtforms import Field, SelectMultipleField
from wtforms.validators import Length
from wtforms.widgets import CheckboxInput, ListWidget

from core.service.logger import get_logger
from core.ui.form_utils import validation_attrs

log = get_logger()

# ==================== Separated Date ==================== #


class SeperatedDate:
    input_type = "text"
    validation_attrs = validation_attrs

    def __init__(self) -> None:
        pass

    def __call__(
        self,
        field: Any,
        month: int | None = None,
        day: int | None = None,
        year: int | None = None,
        **kwargs: dict[str, Any],
    ) -> Markup:
        kwargs.setdefault("id", field.id)
        assert "value" not in kwargs
        date = field._value()
        if date:
            year, month, day = date.split("-")
        flags = getattr(field, "flags", {})
        for k in dir(flags):
            if k in self.validation_attrs and k not in kwargs:
                kwargs[k] = getattr(flags, k)

        disabled = "disabled" if kwargs.get("disabled") else ""

        date_field = (
            f'<div class="seperate-date-field">'
            f'<input class="small-input" min=1 max=12 placeholder="mm" name="{field.name}" type="number" id="{field.id}-month" value="{month}" {disabled}/>-'
            f'<input class="small-input" min=1 max=31 placeholder="dd" name="{field.name}" type="number" id="{field.id}-day" value="{day}" {disabled}/>-'
            f'<input class="small-input" min=2000 max=3000 placeholder="yyyy" name="{field.name}" type="number" id="{field.id}-year" value="{year}" {disabled}/>'
            f"</div>"
        )

        return Markup(date_field)


class SeperateDateField(Field):
    widget = SeperatedDate()

    def process_formdata(self, valuelist: list[str]) -> None:
        if not valuelist:
            return

        date_str = " ".join(valuelist)
        try:
            self.data: datetime.date | None = datetime.datetime.strptime(
                date_str, "%m %d %Y"
            ).date()
            return
        except ValueError:
            self.data = None

        raise ValueError(self.gettext("Not a valid date value."))

    def _value(self) -> str:
        return str(self.data) if self.data is not None else ""


# ==================== Multi Checkbox ==================== #


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for validator in self.validators:
            if isinstance(validator, Length) and getattr(validator, "min", 0) >= 1:
                validator.message = "Please select at least one option"
                self.flags.required = True
                break


# ==================== ReCaptcha ==================== #


class ReCaptchaWidget:
    """Widget to render the reCAPTCHA div"""

    def __call__(self, field, **kwargs):
        site_key = current_app.config.get("RECAPTCHA_SITE_KEY")
        html_attrs = " ".join(f'{k}="{v}"' for k, v in kwargs.items())

        css_class = kwargs.pop("class", "") or kwargs.pop("class_", "")
        if css_class:
            css_class = f"g-recaptcha {css_class}"
        else:
            css_class = "g-recaptcha"

        return Markup(f'<div class="{css_class}" data-sitekey="{site_key}" {html_attrs}></div>')


class ReCaptchaField(Field):
    """A field that handles Google reCAPTCHA v2 validation"""

    type = "ReCaptchaField"
    widget = ReCaptchaWidget()

    def process_formdata(self, valuelist):
        self.data = request.form.get("g-recaptcha-response", "")

    def validate(self, form, extra_validators=()) -> bool:
        if not super().validate(form, extra_validators):
            return False

        if current_app.config.get("TESTING", False):
            return True

        if not self.data:
            self.errors.append("Please complete the security check")  # type: ignore
            return False

        try:
            response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data=dict(
                    secret=current_app.config.get("RECAPTCHA_SECRET_KEY"),
                    response=self.data,
                ),
                timeout=5,
            )
            response.raise_for_status()
            result = response.json()

            if not result.get("success", False):
                error_codes = result.get("error-codes", ["unknown"])
                if "missing-input-response" in error_codes:
                    self.errors.append("Please complete the security check")  # type: ignore
                elif "invalid-input-response" in error_codes:
                    self.errors.append("Security check failed. Please try again")  # type: ignore
                elif "timeout-or-duplicate" in error_codes:
                    self.errors.append("Security check expired. Please try again")  # type: ignore
                else:
                    self.errors.append("Security check failed. Please try again")  # type: ignore
                return False

        except requests.RequestException as e:
            # Don't block users if Google's service is down
            log.error(f"reCAPTCHA verification request failed: {e}")

        return True
