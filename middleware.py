"""
Middleware для бота.
"""
import time
import logging
from typing import Any, Awaitable, Callable, Dict

from cachetools import TTLCache
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)

# Константы для rate limiting
CACHE_MAX_SIZE = 10000  # Максимум пользователей в кэше
CACHE_TTL = 600  # Время жизни записи в кэше (10 минут)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Rate limiting middleware.
    Ограничивает количество запросов от одного пользователя.
    Использует TTLCache для автоматической очистки старых записей.
    """

    def __init__(
        self,
        rate_limit: float = 0.5,  # Минимальный интервал между запросами (секунды)
        max_requests: int = 30,   # Максимум запросов в окне
        window: int = 60,         # Окно в секундах
    ):
        self.rate_limit = rate_limit
        self.max_requests = max_requests
        self.window = window

        # TTLCache автоматически удаляет записи через CACHE_TTL секунд неактивности
        self._cache: TTLCache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем user_id из события
        user_id = self._get_user_id(event)
        if user_id is None:
            return await handler(event, data)

        now = time.time()

        # TTLCache не поддерживает defaultdict, проверяем наличие ключа
        if user_id not in self._cache:
            self._cache[user_id] = {"last": 0, "count": 0, "window_start": 0}

        user_data = self._cache[user_id]

        # Проверка минимального интервала между запросами
        if now - user_data["last"] < self.rate_limit:
            logger.debug(f"Rate limit hit for user (too fast)")
            return await self._on_throttled(event, "too_fast")

        # Проверка количества запросов в окне
        if now - user_data["window_start"] > self.window:
            # Новое окно
            user_data["window_start"] = now
            user_data["count"] = 0

        if user_data["count"] >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user (max requests)")
            return await self._on_throttled(event, "max_requests")

        # Обновляем счётчики
        user_data["last"] = now
        user_data["count"] += 1

        return await handler(event, data)

    def _get_user_id(self, event: TelegramObject) -> int | None:
        """Извлечь user_id из события."""
        if isinstance(event, Message):
            return event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            return event.from_user.id
        return None

    async def _on_throttled(self, event: TelegramObject, reason: str) -> None:
        """Обработка превышения лимита."""
        if isinstance(event, CallbackQuery):
            try:
                if reason == "too_fast":
                    await event.answer("Подожди немного...", show_alert=False)
                else:
                    await event.answer("Слишком много запросов. Попробуй позже.", show_alert=True)
            except Exception:
                pass
        # Для Message просто игнорируем (не отвечаем чтобы не спамить)
