"""
Main initialization file for the webapp, functionally an __init__.py
Runs the factory to build the app, and runs a debug server.
"""

import os

from config import config
from core.app.factory import create_app
from core.service.logger import get_logger

app = create_app()

log = get_logger("app")

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        log.i("Reloaded")
    else:
        log.i(f"Running on {config.BASE_URL}")

    app.run(debug=True, host=config.FLASK_RUN_HOST, port=config.FLASK_RUN_PORT)
