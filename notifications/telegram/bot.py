import asyncio
import functools
import logging
import os
import threading

from django.conf import settings
from telegram import Bot

log = logging.getLogger(__name__)


def telegram_configured():
    token = settings.TELEGRAM_TOKEN or ""
    return bool(token) and not token.endswith("MOCK_TOKEN_REPLACE_ME")


class SyncBot:
    """Synchronous wrapper for async telegram.Bot."""

    def __init__(self, token, **bot_kwargs):
        self._bot_kwargs = {"token": token, **bot_kwargs}
        self._bot = Bot(**self._bot_kwargs)
        self._initialized = False
        self._lock = threading.Lock()
        self._loop = None
        self._thread = None
        self._owner_pid = None

    def _ensure_loop(self):
        pid = os.getpid()
        if self._loop is None or self._owner_pid != pid:
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
            self._thread.start()
            self._owner_pid = pid
            self._initialized = False
            self._bot = Bot(**self._bot_kwargs)

    def _ensure_initialized(self):
        self._ensure_loop()
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    future = asyncio.run_coroutine_threadsafe(self._bot.initialize(), self._loop)
                    future.result()
                    self._initialized = True

    def __getattr__(self, name):
        self._ensure_initialized()
        attr = getattr(self._bot, name)
        if asyncio.iscoroutinefunction(attr):
            wrapper = self._wrap_async(attr)
            setattr(self, name, wrapper)
            return wrapper
        return attr

    def _wrap_async(self, method):
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            self._ensure_loop()
            future = asyncio.run_coroutine_threadsafe(method(*args, **kwargs), self._loop)
            return future.result()
        return wrapper


bot = SyncBot(token=settings.TELEGRAM_TOKEN) if telegram_configured() else None
