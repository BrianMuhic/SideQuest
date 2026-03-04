import json
import re
from typing import Any

from flask import (
    Flask,
    Response,
    make_response,
    render_template,
    url_for,
)
from markupsafe import Markup

JSGLUE_JS_PATH = "/jsglue/jsglue.js"
JSGLUE_NAMESPACE = "Flask"
rule_parser = re.compile(r"<(.+?)>")
splitter = re.compile(r"<.+?>")


def get_routes(app: Flask) -> list[tuple[Any, list[Any], list[Any]]]:
    output = []
    for r in app.url_map.iter_rules():
        endpoint = r.endpoint
        if app.config["APPLICATION_ROOT"] == "/" or not app.config["APPLICATION_ROOT"]:
            rule = r.rule
        else:
            rule = f"{app.config['APPLICATION_ROOT']}{r.rule}"
        rule_args = [x.split(":")[-1] for x in rule_parser.findall(rule)]
        rule_tr = splitter.split(rule)
        output.append((endpoint, rule_tr, rule_args))
    return sorted(output, key=lambda x: len(x[1]), reverse=True)


class JSGlue:
    def __init__(self, app: Flask | None = None) -> None:
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        self.app = app

        @app.route(JSGLUE_JS_PATH)
        def serve_js() -> Response:
            return make_response((self.generate_js(), 200, {"Content-Type": "text/javascript"}))

        @app.context_processor
        def context_processor() -> dict[str, type[JSGlue]]:
            return {"JSGlue": JSGlue}

    def generate_js(self) -> str:
        rules = get_routes(self.app)  # type: ignore
        # .js files are not autoescaped in flask
        return render_template(
            "jsglue/js_bridge.js",
            namespace=JSGLUE_NAMESPACE,
            rules=json.dumps(rules),
        )

    @staticmethod
    def include() -> Markup:
        js_path = url_for("serve_js")
        return Markup('<script src="%s" type="text/javascript"></script>') % (js_path,)
