import asyncio
import json
import logging
import secrets
from html import unescape
from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.db import close_old_connections, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.error import BadRequest, TelegramError

from bot.config import BOT_PAGE_URL
from categories.models import Category
from common.ai.core import OPENAI_MODEL_SMART
from common.ai.item_parser import parse_item
from common.contacts import CONTACT_MAX_COUNT, CONTACT_MAX_LENGTH, CONTACT_TYPES
from counters import counters
from geo.models import GeoCity, GeoCountry
from items.models import Item
from notifications import notification
from notifications.telegram.common import render_html_message
from search import search
from users.models import User

log = logging.getLogger(__name__)

TITLE_MIN_LENGTH = 8
DRAFT_TIMEOUT = 60 * 60 * 24
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)
PARSING_SLOTS = asyncio.Semaphore(4)


def prepare_listing(author, text):
    close_old_connections()
    try:
        try:
            parsed = parse_item(text, model=OPENAI_MODEL_SMART)
        except Exception:
            log.exception("item parse failed")
            return None, "Не получилось разобрать сообщение. Попробуйте ещё раз."

        close_old_connections()
        if parsed.error.strip():
            return None, parsed.error.strip()

        title = parsed.title.strip()
        category = Category.objects.filter(id=parsed.category.strip(), parent__isnull=True).first()
        subcategory = Category.objects.filter(id=parsed.subcategory.strip(), parent__isnull=False).first()
        country = None
        if parsed.country is not None:
            country_name = parsed.country.strip() or author.country
            if country_name:
                country = (
                    GeoCountry.objects.filter(name__iexact=country_name).first()
                    or GeoCountry.objects.filter(id__iexact=country_name).first()
                )

        missing = []
        if len(title) < TITLE_MIN_LENGTH:
            missing.append("что именно рекомендуете")
        if category is None or subcategory is None or subcategory.root_id != category.id:
            missing.append("категорию")
        if parsed.country is not None and country is None and parsed.country.strip() and not missing:
            return None, f"Не нашёл страну «{parsed.country.strip()}» в Базе."
        if parsed.country is not None and country is None:
            missing.append("страну")
        if missing:
            return None, "Не хватает данных: " + ", ".join(missing) + "."

        city_name = (parsed.city or "").strip()
        city = None
        if country is not None and parsed.city is not None and city_name:
            city = (
                GeoCity.objects.filter(country=country, name__iexact=city_name).first()
                or GeoCity.objects.filter(country=country, id__iexact=city_name).first()
            )

        location = (parsed.location or "").strip()
        if len(location) < 5:
            location = ""
        promo_code = (parsed.promo_code or "").strip()
        if len(promo_code) < 3:
            promo_code = ""
        prefix = parsed.prefix if parsed.prefix in dict(Item.PREFIXES) else ""

        cleaned = []
        for row in parsed.contacts:
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

        fields = {
            "prefix": prefix,
            "title": parsed.title.strip()[:Item._meta.get_field("title").max_length],
            "description": (parsed.description or "").strip()[:5000],
            "location": location[:512],
            "contacts": cleaned,
            "promo_code": promo_code[:Item._meta.get_field("promo_code").max_length],
            "category_id": category.id,
            "subcategory_id": subcategory.id,
            "country_id": country.id if country else "",
            "city_id": city.id if city else "",
        }

        token = secrets.token_hex(8)
        cache.set(f"bot-item-draft:{token}", {
            "telegram_id": str(author.telegram_id),
            "user_id": str(author.id),
            "item_id": str(uuid4()),
            "fields": fields,
        }, DRAFT_TIMEOUT)
        item = Item(**{
            **fields,
            "country_id": fields["country_id"] or None,
            "city_id": fields["city_id"] or None,
        })
        item.author = author
        item.category = category
        item.subcategory = subcategory
        item.country = country
        item.city = city
        params = {}
        for name, value in fields.items():
            if name == "contacts":
                value = json.dumps(value, ensure_ascii=False)
            params[name.removesuffix("_id")] = value
        edit_url = settings.APP_HOST.rstrip("/") + reverse("item_create") + "?" + urlencode(params)
        html = render_html_message(
            "notifications/telegram/messages/_item_full.html",
            item=item,
        )
        return {"html": html, "token": token, "edit_url": edit_url}, ""
    finally:
        close_old_connections()


def publish_draft(token):
    close_old_connections()
    key = f"bot-item-draft:{token}"
    stored = cache.get(key)
    if not stored:
        close_old_connections()
        return None, "Это предложение уже не действует.", False

    try:
        author = User.objects.filter(id=stored["user_id"]).first()
        fields = stored["fields"]
        category = Category.objects.filter(id=fields["category_id"], parent__isnull=True).first()
        subcategory = Category.objects.filter(id=fields["subcategory_id"], parent__isnull=False).first()
        country = GeoCountry.objects.filter(id=fields["country_id"]).first() if fields["country_id"] else None
        city = None
        if fields["city_id"] and country is not None:
            city = GeoCity.objects.filter(id=fields["city_id"], country=country).first()
        if author is None or author.is_banned or category is None or subcategory is None:
            return None, "Не получилось опубликовать. Отправьте сообщение ещё раз.", False
        if fields["country_id"] and country is None:
            return None, "Не получилось опубликовать. Отправьте сообщение ещё раз.", False
        if str(author.telegram_id) != stored["telegram_id"] or subcategory.root_id != category.id:
            return None, "Не получилось опубликовать. Отправьте сообщение ещё раз.", False

        # Keep this handler serialized with cancel; parsing handlers run independently.
        # A stable ID makes retries safe after an ambiguous database failure.
        with transaction.atomic():
            item, created = Item.objects.get_or_create(
                id=stored["item_id"],
                defaults={
                    **fields,
                    "prefix": fields["prefix"] or None,
                    "country_id": country.id if country else None,
                    "city_id": city.id if city else None,
                    "author": author,
                    "visibility": Item.VISIBILITY_VISIBLE,
                    "published_at": timezone.now(),
                },
            )
            if created:
                search.update_item_index(item)
                counters.item_created(item)
        if created:
            try:
                notification.item_created(item)
            except Exception:
                log.exception("item %s published, but notifications failed", item.id)
        cache.delete(key)
        return item, "", False
    except Exception:
        log.exception("item publish failed")
        cache.set(key, stored, DRAFT_TIMEOUT)
        return None, "Не получилось опубликовать. Попробуйте ещё раз.", True
    finally:
        close_old_connections()


async def command_add(update, context):
    message = update.effective_message
    if not message or not update.effective_user or update.effective_user.is_bot:
        return

    comment = " ".join(context.args or []).strip()
    source = message.reply_to_message
    if message.chat.type != "private" and source is None:
        await message.reply_text(
            "Ответьте командой /add на сообщение с рекомендацией. "
            "После команды можно дописать свой комментарий."
        )
        return

    content = (source.text or source.caption or "").strip() if source else comment
    await answer_listing(message, source or message, content, comment if source else "")


async def private_message(update, context):
    message = update.effective_message
    if not message or not update.effective_user or update.effective_user.is_bot:
        return
    await answer_listing(message, message, (message.text or message.caption or "").strip())


async def answer_listing(message, source, content, comment=""):
    if not content and not comment:
        await message.reply_text("В сообщении нет текста, из которого можно собрать объявление.")
        return

    author = await User.objects.filter(telegram_id=str(message.from_user.id)).afirst()
    if author is None:
        await message.reply_text(
            "Сначала привяжите бота к аккаунту Базы, потом пришлите рекомендацию ещё раз.\n"
            f"{BOT_PAGE_URL}"
        )
        return

    if author.is_banned:
        await message.reply_text("Вы забанены и не можете добавлять объявления.")
        return

    chat_names = []
    for candidate in (source, message):
        origin = candidate.forward_origin
        origin_chat = getattr(origin, "sender_chat", None) or getattr(origin, "chat", None)
        for chat in (origin_chat, candidate.chat):
            if chat and chat.type != "private" and chat.title and chat.title not in chat_names:
                chat_names.append(chat.title)
    blocks = []
    if chat_names:
        blocks.append("Чат: " + ", ".join(chat_names))
    if comment:
        blocks.append("Комментарий того, кто добавляет:\n" + comment)
    if content:
        blocks.append("Сообщение:\n" + content)
    text = "\n\n".join(blocks)

    await message.reply_chat_action("typing")
    await message.reply_text("Посмотрим, парсю сообщение...")

    try:
        async with PARSING_SLOTS:
            preview, error = await asyncio.to_thread(prepare_listing, author, text)
    except Exception:
        log.exception("item preview failed")
        await message.reply_text("Не получилось подготовить карточку. Попробуйте ещё раз.")
        return
    if error:
        await message.reply_text(error[:2000])
        return

    token = preview["token"]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Постим", callback_data=f"add:post:{token}")],
        [InlineKeyboardButton("✏️ Отредактировать", url=preview["edit_url"])],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"add:cancel:{token}")],
    ])
    html = preview["html"]
    try:
        if len(html.encode("utf-16-le")) // 2 <= 4096:
            await message.reply_text(html, parse_mode="HTML", reply_markup=keyboard, link_preview_options=NO_PREVIEW)
        else:
            # Long previews retain every field without cutting HTML tags or entities.
            text = unescape(strip_tags(html))
            chunks = [text[index:index + 2000] for index in range(0, len(text), 2000)]
            for index, chunk in enumerate(chunks):
                await message.reply_text(chunk,
                    reply_markup=keyboard if index == len(chunks) - 1 else None,
                    link_preview_options=NO_PREVIEW,
                )
    except TelegramError:
        log.exception("item preview delivery failed")
        await message.reply_text("Не получилось отправить предпросмотр. Попробуйте ещё раз.")


async def draft_callback(update, context):
    query = update.callback_query
    action, token = (query.data or "").split(":", 2)[1:]
    stored = cache.get(f"bot-item-draft:{token}")
    if not stored:
        await query.answer("Это предложение уже не действует", show_alert=True)
        return
    if not query.from_user or str(query.from_user.id) != str(stored["telegram_id"]):
        await query.answer("Это не ваша карточка", show_alert=True)
        return

    await query.answer()
    if action == "cancel":
        cache.delete(f"bot-item-draft:{token}")
        text = "Отменил. Ничего не публикую."
        keep_buttons = False
    else:
        item, error, keep_buttons = await asyncio.to_thread(publish_draft, token)
        if error:
            text = error
        else:
            url = settings.APP_HOST.rstrip("/") + item.get_absolute_url()
            text = f"Добавил в Базу: {item.title}\n{url}"

    if not keep_buttons:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest as error:
            if "message is not modified" not in str(error).lower():
                log.warning("Could not remove draft buttons: %s", error)
        except TelegramError:
            log.exception("Could not remove draft buttons")
    await query.message.reply_text(text)
