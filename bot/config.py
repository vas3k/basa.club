from django.conf import settings
from django.urls import reverse

BOT_PAGE_URL = f"{settings.APP_HOST.rstrip('/')}{reverse('bot')}"

WELCOME_MESSAGE = (
    "Привет, я бот Вастрик 💽 Базы.\n"
    "Чтобы привязать меня к аккаунту, откройте страницу и нажмите кнопку:\n"
    f"{BOT_PAGE_URL}"
)
