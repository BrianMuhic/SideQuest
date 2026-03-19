from wtforms import (
    EmailField,
    PasswordField,
    StringField,
    ValidationError,
)
from wtforms.validators import (
    DataRequired,
    Email,
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
    email = EmailField(
        "Email", filters=[str_strip, str_lower], validators=[Email(), DataRequired()]
    )
    password = PasswordField("Password", filters=[str_strip], validators=[DataRequired()])

    def validate(self, extra_validators=None) -> bool:
        if not super().validate(extra_validators):
            return False

        user = User.with_email(self.db, self.email.data)
        if not user or not user.check_password(self.password.data):
            return form_error(self.email, "Invalid email or password")

        self.user = user

        return True

    def export(self) -> User:
        return self.user


class BaseRegistrationForm(BaseForm):
    first_name = StringField("First Name", filters=[str_strip], validators=[Length(min=1, max=256)])
    last_name = StringField("Last Name", filters=[str_strip], validators=[Length(min=1, max=256)])


class InitialRegistrationForm(BaseRegistrationForm):
    email = EmailField(
        "Email Address",
        filters=[str_strip, str_lower],
        validators=[Email(), Length(min=1, max=256)],
    )
    verify_email = EmailField(
        "Verify Email", filters=[str_strip, str_lower], validators=[EqualTo("email")]
    )

    password = PasswordField(
        "Password",
        filters=[str_strip],
        validators=[Length(min=4, max=256)],
    )
    verify_password = PasswordField(
        "Repeat Password", filters=[str_strip], validators=[EqualTo("password")]
    )

    def validate_email(self, field: EmailField) -> None:
        if User.with_email(self.db, field.data):
            raise ValidationError("This email already exists")

    def export(self) -> User:
        user = User(
            email=self.email.data,
            first_name=self.first_name.data,
            last_name=self.last_name.data,
        )
        user.set_password(self.password.data)
        user.add(self.db, flush=True)

        log.i(f"Registered {user}")

        return user


# class EditRegistrationForm(BaseRegistrationForm):
#     email = EmailField("Email Address", render_kw=readonly_attrs)

#     _user: User

#     def __init__(self, db: Session, user_id: int | None, **kwargs):
#         super().__init__(db, **kwargs)

#         user = require_user()
#         if user_id and user.is_admin:
#             user = User.get_one(db, user_id)
#         self._user = user

#     def import_(self) -> None:
#         self.email.data = self._user.email
#         self.first_name.data = self._user.first_name
#         self.last_name.data = self._user.last_name

#     def export(self) -> None:
#         self._user.first_name = self.first_name.data
#         self._user.last_name = self.last_name.data


# class ChangePasswordForm(BaseForm):
#     current_password = PasswordField("Password", filters=[str_strip], validators=[DataRequired()])
#     new_password = PasswordField(
#         "New Password",
#         filters=[str_strip],
#         validators=[Length(min=4, max=256)],
#     )
#     verify_new_password = PasswordField(
#         "Repeat New Password", filters=[str_strip], validators=[EqualTo("new_password")]
#     )

#     _user: User

#     def __init__(self, db: Session, user_id: int | None, **kwargs):
#         super().__init__(db, **kwargs)

#         user = require_user()
#         if user.is_admin and user_id:
#             user = User.get_one(db, user_id)
#         self._user = user

#     def validate_current_password(self, field: PasswordField) -> None:
#         if not self._user.check_password(field.data):
#             raise ValidationError("Invalid password")

#     def export(self) -> None:
#         self._user.set_password(self.new_password.data)
#         log.i(f"Change password for {self._user}")


# class ForgotPasswordForm(BaseForm):
#     email = EmailField(
#         "Email Address",
#         filters=[str_strip, str_lower],
#         validators=[Email(), DataRequired()],
#     )

#     def export(self) -> str:
#         return self.email.data


# class ResetPasswordForm(BaseForm):
#     password = PasswordField("Password", filters=[str_strip], validators=[Length(min=4, max=256)])
#     verify_password = PasswordField(
#         "Repeat Password", filters=[str_strip], validators=[EqualTo("password")]
#     )

#     def export(self) -> str:
#         return self.password.data
