from wtforms import (
    PasswordField,
    StringField,
    ValidationError,
)
from wtforms.validators import (
    DataRequired,
    EqualTo,
    Length,
)

from account.models import User
from core.service.logger import get_logger
from core.ui.base_form import BaseForm
from core.ui.form_utils import (
    form_error,
    str_lower,
    str_strip,
)

log = get_logger()


class LoginForm(BaseForm):
    login = StringField(
        "Login",
        filters=[str_strip, str_lower],
        validators=[DataRequired()],
    )
    password = PasswordField(
        "Password",
        filters=[str_strip],
        validators=[DataRequired()],
    )

    def validate(self, extra_validators=None) -> bool:
        if not super().validate(extra_validators):
            return False

        login_value: str = self.login.data

        user = User.with_username(self.db, login_value) or User.with_email(self.db, login_value)

        if not user or not user.check_password(self.password.data):  # type: ignore
            return form_error(self.login, "Invalid username or email or password")

        self.user = user

        return True

    def export(self) -> User:
        return self.user


class InitialRegistrationForm(BaseForm):
    username = StringField(
        "Username",
        filters=[str_strip, str_lower],
        validators=[Length(min=1, max=256)],
    )
    email = StringField(
        "Email",
        filters=[str_strip, str_lower],
        validators=[DataRequired()],
    )
    password = PasswordField(
        "Password",
        filters=[str_strip],
        validators=[Length(min=4, max=256)],
    )
    verify_password = PasswordField(
        "Repeat Password", filters=[str_strip], validators=[EqualTo("password")]
    )

    def validate_username(self, field: StringField) -> None:
        if User.with_username(self.db, field.data):  # type: ignore
            raise ValidationError("This username is already taken")

    def export(self) -> User:
        user = User(
            username=self.username.data,
            email=self.email.data,
        )
        user.set_password(self.password.data)  # type: ignore
        user.add(self.db, flush=True)

        log.i(f"Registered {user}")

        return user


class ForgotPasswordForm(BaseForm):
    username = StringField(
        "Username",
        filters=[str_strip, str_lower],
        validators=[DataRequired()],
    )

    def export(self) -> str:
        return self.username.data  # type: ignore


class ResetPasswordForm(BaseForm):
    password = PasswordField(
        "Password",
        filters=[str_strip],
        validators=[Length(min=4, max=256)],
    )

    confirm_password = PasswordField(
        "Repeat Password",
        filters=[str_strip],
        validators=[EqualTo("password")],
    )

    def export(self) -> str:
        return self.password.data  # type: ignore
