import logging
from datetime import datetime, timedelta
from typing import Any

from flask import Flask, redirect, url_for
from flask.config import Config
from flask_assets import Bundle, Environment
from pydantic_settings import BaseSettings
from sqlalchemy import text

from blueprints import BLUEPRINTS
from config import config
from constant import LOCAL_ZONEINFO
from core.app import endpoint
from core.app.errors import register_error_handlers
from core.app.extensions import extensions
from core.db.engine import close_request_session, db_session, init_engine
from core.service.logger import config_logger, set_log_level
from core.ui.filters import add_template_filters
from navbar import get_navbar


class AttrConfig(Config):
    # https://stackoverflow.com/questions/58417133/access-flask-config-as-attributes-rather-than-dict-keys
    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError(key) from e


class CustomFlask(Flask):
    config_class = AttrConfig


def _setup_logging() -> None:
    config_logger(config)

    set_log_level(
        logging.CRITICAL,
        "sqlalchemy.pool.impl.QueuePool",
        "fontTools",
    )

    set_log_level(
        logging.WARNING,
        "werkzeug",
        "urllib3.connectionpool",
    )


def _setup_assets(app: CustomFlask) -> None:
    assets = Environment(app)
    assets.url = app.static_url_path

    assets.auto_build = app.config.get("DEBUG", False)

    bundles = dict(
        scss=Bundle(
            "scss/main.scss",
            filters="libsass,cssmin",
            output="build/styles.min.css",
            depends=["scss/*.scss", "scss/*/*.scss"],
        ),
        js=Bundle(
            "js/*.js",
            filters="rjsmin",
            output="build/core.min.js",
            depends=["js/*.js", "js/*/*.js"],
        ),
    )

    assets.register(bundles)

    # Build on startup to ensure files exist
    for bundle in bundles.values():
        bundle.build()


def _setup_jinja(app: CustomFlask) -> None:
    app.jinja_options["line_statement_prefix"] = ">>"
    app.jinja_options["line_comment_prefix"] = "##"
    app.jinja_env.add_extension("jinja2.ext.loopcontrols")
    add_template_filters(app)

    @app.context_processor
    def _inject_globals() -> dict[str, Any]:
        return dict(
            navbar=get_navbar(),
            mail_redirect=config.MAIL_REDIRECT_TO_DEVELOPER,
            endpoint=endpoint,
            now=datetime.now(LOCAL_ZONEINFO),
            img_url=lambda name: url_for("static", filename=f"img/{name}"),
        )


def _setup_file_routes(app: CustomFlask) -> None:
    file_routes = [
        ("favicon", "/favicon.ico", "/static/img/favicon.ico"),
        ("apple_touch_icon", "/apple-touch-icon.png", "/static/img/apple-touch-icon.png"),
        ("robots", "/robots.txt", "/static/robots.txt"),
    ]
    for name, route, file in file_routes:
        app.add_url_rule(route, endpoint=name, view_func=lambda file=file: redirect(file))


def _setup_extensions(app: CustomFlask) -> None:
    for extension in extensions:
        extension.init_app(app)


def _setup_blueprints(app: CustomFlask) -> None:
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)


def _setup_db(app: CustomFlask) -> None:
    if app.config.get("TESTING"):
        return

    init_engine(app.config)

    with db_session() as db:
        if db.execute(text("SELECT GET_LOCK('app_init', 10)")).scalar() != 1:
            return
        try:
            # Call any methods that need to run on app start here
            pass
        finally:
            db.execute(text("SELECT RELEASE_LOCK('app_init')"))


def create_app(alt_config: Config | BaseSettings | None = None) -> Flask:
    app = CustomFlask(
        __name__,
        static_url_path="/static",
        static_folder="../../static",
        template_folder="../templates",
    )

    app.config.from_object(alt_config or config)
    app.teardown_appcontext(close_request_session)
    app.permanent_session_lifetime = timedelta(minutes=config.USER_SESSION_TIMEOUT_MINUTES)

    register_error_handlers(app)
    _setup_logging()
    _setup_jinja(app)
    _setup_assets(app)
    _setup_extensions(app)
    _setup_blueprints(app)
    _setup_db(app)
    _setup_file_routes(app)

    return app
