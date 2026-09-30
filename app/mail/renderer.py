from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

environment = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(
        enabled_extensions=("html",),
    ),
)


def render_template(
    template_name: str,
    **context: object,
) -> str:
    template = environment.get_template(
        template_name,
    )

    return template.render(
        **context,
    )
