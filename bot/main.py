import logging
import os
import sys

import django

# IMPORTANT: this should go before any django-related imports (models, apps, settings)
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vas3k_base.settings")
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
django.setup()

from django.conf import settings
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.handlers import auth, help, items, notifications

log = logging.getLogger(__name__)


def main() -> None:
    if not settings.TELEGRAM_TOKEN or settings.TELEGRAM_TOKEN.endswith("MOCK_TOKEN_REPLACE_ME"):
        log.error("TELEGRAM_TOKEN is not set. Put the bot token in the environment and start again.")
        raise SystemExit(1)

    application = Application.builder().token(settings.TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", auth.command_start, filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("help", help.command_help, filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("add", items.command_add))
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
        items.private_message,
    ))
    application.add_handler(CallbackQueryHandler(auth.confirm_callback, pattern=r"^link:.+"))
    application.add_handler(CallbackQueryHandler(notifications.unsubscribe_callback, pattern=r"^unsub:"))
    if settings.DEBUG:
        application.run_polling()
    else:
        application.run_webhook(
            listen=settings.TELEGRAM_BOT_WEBHOOK_HOST,
            port=settings.TELEGRAM_BOT_WEBHOOK_PORT,
            url_path=settings.TELEGRAM_TOKEN,
            webhook_url=settings.TELEGRAM_BOT_WEBHOOK_URL + settings.TELEGRAM_TOKEN,
        )


if __name__ == "__main__":
    main()
