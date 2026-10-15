import asyncio
import logging

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from bot.config import BOT_PAGE_URL
from categories.models import Category
from common.ai.core import OPENAI_MODEL_SMART
from common.ai.item_parser import parse_item
from common.contacts import CONTACT_MAX_COUNT, CONTACT_MAX_LENGTH, CONTACT_TYPES
from counters import counters
from geo.models import GeoCity, GeoCountry
from items.models import Item
from notifications import notification
from search import search
from telegram.error import TimedOut
from users.models import User

log = logging.getLogger(__name__)

TITLE_MIN_LENGTH = 8


def linked_user(telegram_user):
    if not telegram_user:
        return None
    return User.objects.filter(telegram_id=str(telegram_user.id)).first()


def origin_chat_title(message):
    origin = getattr(message, "forward_origin", None) if message else None
    if origin is None:
        return ""
    sender_chat = getattr(origin, "sender_chat", None) or getattr(origin, "chat", None)
    return (getattr(sender_chat, "title", None) or "").strip()


def place_names(source, command_message):
    names = []
    for message in (source, command_message):
        if message is None:
            continue
        title = origin_chat_title(message)
        if title and title not in names:
            names.append(title)
        chat = message.chat
        if chat and chat.type != "private" and chat.title and chat.title not in names:
            names.append(chat.title)
    return names


def listing_input(content, comment, chat_names):
    blocks = []
    if chat_names:
        blocks.append("Чат: " + ", ".join(chat_names))
    if comment:
        blocks.append("Комментарий того, кто добавляет:\n" + comment.strip())
    if content:
        blocks.append("Сообщение:\n" + content.strip())
    return "\n\n".join(blocks).strip()


def message_text(message):
    if not message:
        return ""
    return (message.text or message.caption or "").strip()


def find_country(name):
    name = (name or "").strip()
    if not name:
        return None
    return (
        GeoCountry.objects.filter(name__iexact=name).first()
        or GeoCountry.objects.filter(pk__iexact=name).first()
    )


def find_city(name, country):
    name = (name or "").strip()
    if not name or country is None:
        return None
    return (
        GeoCity.objects.filter(country=country, name__iexact=name).first()
        or GeoCity.objects.filter(country=country, pk__iexact=name).first()
    )


def clean_contacts(rows):
    cleaned = []
    for row in rows or []:
        text = (row.text or "").strip()
        comment = (row.comment or "").strip()
        if len(text) < 3:
            continue
        contact_type = row.type if row.type in CONTACT_TYPES else "custom"
        cleaned.append({
            "type": contact_type,
            "text": text[:CONTACT_MAX_LENGTH],
            "comment": comment[:CONTACT_MAX_LENGTH],
        })
        if len(cleaned) >= CONTACT_MAX_COUNT:
            break
    return cleaned


def rejection(parsed, author):
    if (parsed.error or "").strip():
        return parsed.error.strip()

    title = (parsed.title or "").strip()
    category = Category.objects.filter(pk=(parsed.category or "").strip(), parent__isnull=True).first()
    subcategory = Category.objects.filter(pk=(parsed.subcategory or "").strip(), parent__isnull=False).first()
    country = find_country(parsed.country)
    if country is None and not (parsed.country or "").strip():
        country = find_country(author.country)

    missing = []
    if len(title) < TITLE_MIN_LENGTH:
        missing.append("что именно рекомендуете")
    if category is None or subcategory is None or subcategory.root_id != category.id:
        missing.append("категорию")
    if country is None and (parsed.country or "").strip() and not missing:
        return f"Не нашёл страну «{parsed.country.strip()}» в Базе."
    if country is None:
        missing.append("страну")
    if missing:
        return "Не хватает данных: " + ", ".join(missing) + "."
    return ""


def publish_parsed_item(author, parsed):
    title = parsed.title.strip()
    category = Category.objects.filter(pk=parsed.category.strip(), parent__isnull=True).first()
    subcategory = Category.objects.filter(pk=parsed.subcategory.strip(), parent__isnull=False).first()
    country = find_country(parsed.country)
    if country is None:
        country = find_country(author.country)
    city = find_city(parsed.city, country)

    location = (parsed.location or "").strip()
    if len(location) < 5:
        location = ""
    promo_code = (parsed.promo_code or "").strip()
    if len(promo_code) < 3:
        promo_code = ""

    prefix = parsed.prefix if parsed.prefix in dict(Item.PREFIXES) else None
    item = Item(
        prefix=prefix,
        title=title[:Item._meta.get_field("title").max_length],
        description=(parsed.description or "").strip(),
        location=location[:Item._meta.get_field("location").max_length],
        contacts=clean_contacts(parsed.contacts),
        promo_code=promo_code[:Item._meta.get_field("promo_code").max_length],
        category=category,
        subcategory=subcategory,
        country=country,
        city=city,
        author=author,
        visibility=Item.VISIBILITY_VISIBLE,
        published_at=timezone.now(),
    )
    item.save()
    search.update_item_index(item)
    counters.item_created(item)
    notification.item_created(item)
    return item


def add_listing(author, text):
    close_old_connections()
    try:
        try:
            parsed = parse_item(text, model=OPENAI_MODEL_SMART)
        except Exception:
            log.exception("item parse failed")
            return None, "Не получилось разобрать сообщение. Попробуйте ещё раз."

        close_old_connections()
        reason = rejection(parsed, author)
        if reason:
            return None, reason
        return publish_parsed_item(author, parsed), ""
    finally:
        close_old_connections()


def item_url(item):
    return settings.APP_HOST.rstrip("/") + item.get_absolute_url()


async def command_add(update, context):
    close_old_connections()
    try:
        message = update.effective_message
        if not message or (update.effective_user and update.effective_user.is_bot):
            return

        comment = " ".join(context.args or []).strip()
        reply = message.reply_to_message
        if message.chat.type != "private" and reply is None:
            await message.reply_text(
                "Ответьте командой /add на сообщение с рекомендацией. "
                "После команды можно дописать свой комментарий."
            )
            return

        content = message_text(reply) if reply else ""
        if reply is None:
            content = comment
            comment = ""
        source = reply or message
        text = listing_input(content, comment, place_names(source, message))
        await answer_listing(message, text)
    finally:
        close_old_connections()


async def private_message(update, context):
    close_old_connections()
    try:
        message = update.effective_message
        if not message or (update.effective_user and update.effective_user.is_bot):
            return
        text = listing_input(message_text(message), "", place_names(message, message))
        await answer_listing(message, text)
    finally:
        close_old_connections()


async def answer_listing(message, text):
    if not text:
        await message.reply_text("В сообщении нет текста, из которого можно собрать объявление.")
        return

    author = linked_user(message.from_user)
    if author is None:
        await message.reply_text(
            "Сначала привяжите бота к аккаунту Базы, потом пришлите рекомендацию ещё раз.\n"
            f"{BOT_PAGE_URL}"
        )
        return

    if author.is_banned:
        await message.reply_text("Вы забанены и не можете добавлять объявления.")
        return

    await message.reply_chat_action("typing")
    await reply(message, "Посмотрим, парсю сообщение...")

    item, error = await asyncio.to_thread(add_listing, author, text)
    if error:
        await reply(message, error[:4096])
        return
    await reply(message, f"Добавил в Базу: {item.title}\n{item_url(item)}")


async def reply(message, text):
    try:
        await message.reply_text(text)
    except TimedOut:
        await message.reply_text(text)
