from flask import render_template
from flask.typing import ResponseReturnValue
from sqlalchemy.orm import Session

from account import service
from account.forms import (
    ForgotPasswordForm,
    InitialRegistrationForm,
    LoginForm,
    ResetPasswordForm,
)
from account.service import guest_required
from core.app.blueprint import BaseBlueprint
from core.db.engine import use_db
from core.service.logger import get_logger

bp = BaseBlueprint("account", url_prefix="/account")
log = get_logger()

# ============================== Authentication ============================== #


@bp.before_app_request
def before_request() -> ResponseReturnValue | None:
    service.user_session_timeout()


@bp.post("/login")
@use_db
def login(db: Session) -> ResponseReturnValue:
    form = LoginForm(db)
    if form.validate():
        user = form.export()
        service.login(user)
        return {"username": user.username}
    return form.errors, form.status_code


@bp.post("/logout")
def logout() -> ResponseReturnValue:
    service.logout()
    return "done"


# ============================== Account Management ============================== #


@bp.post("/register")
@guest_required
@use_db
def register(db: Session) -> ResponseReturnValue:
    form = InitialRegistrationForm(db)
    if form.validate():
        user = form.export()
        service.login(user)
        return {"username": user.username}
    return form.errors, form.status_code


@bp.post("/forgot-password")
@guest_required
@use_db
def forgot_password_route(db: Session):
    form = ForgotPasswordForm(db)

    if form.validate():
        service.forgot_password(db, form.export())
        return {"status": "ok"}

    return form.errors, form.status_code


@bp.post("/reset_password/<access_token>")
@guest_required
@use_db
def reset_password_route(db: Session, access_token: str):
    form = ResetPasswordForm(db)

    if form.validate():
        service.reset_password(db, access_token, form.export())
        return {"status": "password_updated"}

    return form.errors, form.status_code


@bp.get("/reset_password/<access_token>")
@guest_required
def reset_password_page(access_token: str):
    return render_template("reset_password.html", token=access_token)


# @bp.get_post("/edit-registration")
# @bp.get_post("/edit-registration/<int:user_id>")
# @login_required
# @use_db
# def edit_registration(db: Session, user_id: int | None = None) -> ResponseReturnValue:
#     form = EditRegistrationForm(db, user_id)

#     if form.validate_on_submit():
#         form.export()
#         return endpoint.index.redirect()
#     elif not form.is_submitted():
#         form.import_()

#     return render_template(
#         "edit-registration.html",
#         title="Manage Registration",
#         form=form,
#     )


# @bp.get_post("/change-password")
# @bp.get_post("/change-password/<int:user_id>")
# @login_required
# @use_db
# def change_password(db: Session, user_id: int | None = None) -> ResponseReturnValue:
#     form = ChangePasswordForm(db, user_id)

#     if form.validate_on_submit():
#         form.export()
#         return endpoint.account_edit_registration.redirect()

#     return render_template(
#         "change-password.html",
#         title="Change Password",
#         form=form,
#     )
