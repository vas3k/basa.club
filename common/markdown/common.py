import html
import re

ALLOWED_CSS_CLASSES_IN_MARKDOWN = {
    "image-wide",
    "button",
    "button-small",
    "button-big",
    "button-red",
    "button-blue",
    "button-inverted",
    "block",
    "border",
}

SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def split_title_and_css_classes(value) -> tuple[str, list]:
    if value.startswith("."):
        try:
            classes, title = value.split(" ", 1)
        except ValueError:
            classes, title = value, ""
        return title, [
            c for c in html.escape(classes).split(".") if c.strip() and c.strip() in ALLOWED_CSS_CLASSES_IN_MARKDOWN
        ]
    return value, []


def normalize_url(url: str, default_scheme: str = "https") -> str:
    if not url:
        return ""

    url = url.strip()
    if not url:
        return ""

    # Keep absolute paths, hashes and anything that already has a scheme
    if url.startswith(("#", "/")) or SCHEME_RE.match(url):
        return url

    return f"{default_scheme}://{url}"
