from account.routes import bp as account_bp
from landing.routes import bp as landing_bp
from osm.routes import bp as osm_bp

BLUEPRINTS = [
    account_bp,
    landing_bp,
    osm_bp,
]
