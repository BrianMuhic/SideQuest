"""
Module for enrolling extensions for the core template.
See also webapp/extensions

This might be integrated into the factory, but there are complications with flask_login:
  Exception: Missing user_loader or request_loader.
  Refer to http://flask-login.readthedocs.io/#how-it-works for more info.
"""

from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment

from core.app.flask_jsglue import JSGlue

jsglue = JSGlue()
login_manager = LoginManager()
mail = Mail()
moment = Moment()


extensions = (
    jsglue,
    login_manager,
    mail,
    moment,
)
