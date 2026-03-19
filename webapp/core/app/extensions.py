"""
Module for enrolling extensions for the core template.
See also webapp/extensions

This might be integrated into the factory, but there are complications with flask_login:
  Exception: Missing user_loader or request_loader.
  Refer to http://flask-login.readthedocs.io/#how-it-works for more info.
"""

from flask_login import LoginManager
from flask_mail import Mail

login_manager = LoginManager()
mail = Mail()


extensions = (
    login_manager,
    mail,
)
