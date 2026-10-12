import html
import mistune
from urllib.parse import unquote

from common.markdown.common import normalize_url
from common.regexp import USERNAME_RE


class ClubRenderer(mistune.HTMLRenderer):
    """Simple club markdown: text formatting and safe links only. No media or HTML."""

    MEDIA_PLACEHOLDER = "🖼️"

    def __init__(self, uniq_id=None, disable_mentions=False):
        super().__init__(escape=True)
        self.uniq_id = uniq_id
        self.disable_mentions = disable_mentions

    def text(self, text):
        text = html.escape(text)
        if not self.disable_mentions:
            text = USERNAME_RE.sub(r' <a href="/user/\1/">@\1</a>', text)
        return text

    def paragraph(self, text):
        text = text.replace("\n", "<br>\n")
        return f"<p>{text}</p>\n"

    def heading(self, text, level, **attrs):
        tag = f"h{level}"
        return f"<{tag}>{text}</{tag}>\n"

    def link(self, text, url, title=None):
        link = normalize_url(url)
        safe = self.safe_url(link) if link else ""
        if not safe or safe == "#harmful-link" or not safe.startswith(("#", "/", "mailto:", "http://", "https://")):
            return html.escape(text or url or "")

        display = html.escape(unquote(html.unescape(text or link)))
        title_attr = f' title="{html.escape(title)}"' if title else ""
        if safe.startswith(("http://", "https://")):
            rel_attr = ' target="_blank" rel="noopener noreferrer"'
        else:
            rel_attr = ' rel="noopener noreferrer"'
        return f'<a href="{safe}"{title_attr}{rel_attr}>{display}</a>'

    def image(self, text, url, title=None):
        return self.MEDIA_PLACEHOLDER

    def block_html(self, html_text):
        return self.MEDIA_PLACEHOLDER

    def inline_html(self, html_text):
        return self.MEDIA_PLACEHOLDER
