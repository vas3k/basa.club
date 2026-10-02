import html

from common.markdown.club_renderer import ClubRenderer
from common.markdown.common import normalize_url
from common.regexp import IMAGE_RE, TWITTER_RE, VIDEO_RE, YOUTUBE_RE


class EmailRenderer(ClubRenderer):
    """Email-oriented renderer that still allows media embeds."""

    def link(self, text, url, title=None):
        if text == url:
            embed = self.embed(url, text or "", title or "")
            if embed:
                return embed
        return super().link(text, url, title)

    def image(self, text, url, title=None):
        embed = self.embed(url, text, title)
        if embed:
            return embed
        return f'<a href="{self.safe_url(normalize_url(url))}">{html.escape(url)}</a>'

    def block_html(self, html_text):
        return html.escape(html_text)

    def inline_html(self, html_text):
        return html.escape(html_text)

    def embed(self, url, text="", title=None):
        if IMAGE_RE.match(url):
            return self.simple_image(url, text, title)

        if YOUTUBE_RE.match(url):
            return self.youtube(url, text, title)

        if VIDEO_RE.match(url):
            return self.video(url, text, title)

        if TWITTER_RE.match(url):
            return self.tweet(url, text, title)

        return None

    def simple_image(self, url, text="", title=None):
        return (
            f'<img src="{html.escape(url)}" alt="{html.escape(text)}" '
            f'width="600" border="0"><br>{html.escape(title or "")}'
        )

    def youtube(self, url, text="", title=None):
        youtube_match = YOUTUBE_RE.match(url)
        youtube_id = html.escape(youtube_match.group(1) or "")
        return (
            f'<a href="{html.escape(url)}"><span class="ratio-16-9 video-preview" '
            f'style="background-image: url(\'https://img.youtube.com/vi/{youtube_id}/0.jpg\');">'
            f'</span></a><br>{html.escape(title or "")}'
        )

    def video(self, url, text="", title=None):
        return (
            f'<video src="{html.escape(url)}" controls muted playsinline>'
            f'{html.escape(text)}</video><br>{html.escape(title or "")}'
        )

    def tweet(self, url, text="", title=None):
        return f'<a href="{html.escape(url)}">{html.escape(url)}</a><br>{html.escape(title or "")}'

    def heading(self, text, level, **attrs):
        tag = f"h{level}"
        return f"<{tag}>{text}</{tag}>\n"
