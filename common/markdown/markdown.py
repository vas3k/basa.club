import mistune

from common.markdown.club_renderer import ClubRenderer
from common.markdown.email_renderer import EmailRenderer
from common.markdown.plain_renderer import PlainRenderer
from common.markdown.telegram_renderer import TelegramRenderer


def markdown_text(text, renderer=ClubRenderer, uniq_id=None, disable_mentions=False):
    if issubclass(renderer, ClubRenderer):
        renderer_instance = renderer(uniq_id=uniq_id, disable_mentions=disable_mentions)
    else:
        renderer_instance = renderer()

    markdown = mistune.create_markdown(
        escape=True,
        renderer=renderer_instance,
        plugins=["strikethrough", "url"],
    )
    return (markdown(text) or "").strip()


def markdown_plain(text):
    return markdown_text(text, renderer=PlainRenderer)


def markdown_tg(text):
    return markdown_text(text, renderer=TelegramRenderer)


def markdown_email(text):
    return markdown_text(text, renderer=EmailRenderer)
