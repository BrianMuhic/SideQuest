from flask.templating import render_template
from markupsafe import Markup


def render_simple_page(title: str, content: Markup | str = "") -> str:
    """Renders the simple.html template with a title and content."""
    return render_template(
        "simple.html",
        title=title,
        content=Markup(content),
    )
