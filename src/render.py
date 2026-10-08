from __future__ import annotations
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from .pydantic_schema import CallScript

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def render_markdown(script: CallScript) -> str:
    """Render a CallScript into final Markdown using the Jinja2 template.

    Args:
        script (CallScript): The CallScript object to render.
    Returns:
        str: The rendered Markdown string.
    """
    jinja_env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        trim_blocks=True,  # Strip the newline after a {% block %} tag.
        lstrip_blocks=True,  # Strip leading whitespace before a block tag.
    )
    template = jinja_env.get_template("template_script.md.j2")
    rendered = template.render(script=script)
    # Collapse any accidental triple-blank-lines left by conditional blocks.
    rendered = re.sub(r"\n{3,}", "\n\n", rendered)
    return rendered.strip() + "\n"
