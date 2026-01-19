"""
Менеджер контента с кэшированием.

Загружает контент из SQLite (синхронизированный из Notion)
и предоставляет fallback на hardcoded значения.
"""
import asyncio
import logging
import random
from typing import Optional

from sqlalchemy import select

from database import get_session, ContentCache, UITextCache

logger = logging.getLogger(__name__)


# ===== FALLBACK ДАННЫЕ =====
# Используются если Notion недоступен и БД пуста

FALLBACK_PAUSE_SHORT = [
    "в тишине есть место",
    "фокус может ослабевать",
    "свой ритм — тоже ритм",
    "медленно — это тоже путь",
    "пауза может быть точкой опоры",
    "иногда достаточно оставить всё как есть",
    "можно замедлиться, даже если вокруг никто не замедляется",
    "спокойствие может приходить само",
    "иногда забота — это не делать",
    "пауза может случаться просто так",
    "простое присутствие имеет ценность",
    "к себе можно возвращаться медленно",
]

FALLBACK_PAUSE_LONG = [
    """О счастье мы всегда лишь вспоминаем.
А счастье всюду. Может быть, оно —
Вот этот сад осенний за сараем
И чистый воздух, льющийся в окно.

В бездонном небе лёгким белым краем
Встаёт, сияет облако. Давно
Слежу за ним… Мы мало видим, знаем,
А счастье только знающим дано.

Иван Бунин""",
]

FALLBACK_BREATHE = [
    "https://soundcloud.com/aleksandra-ermolenko/pauza-dekabr?in=aleksandra-ermolenko%2Fsets%2Fpauza&si=a3094c0bc9f84f0fbad941be6fbdd883&utm_source=clipboard&utm_medium=text&utm_campaign=social_sharing",
]

FALLBACK_MOVIES = [
    "https://www.imdb.com/title/tt5247022",
]

FALLBACK_BOOKS = [
    "https://www.dropbox.com/scl/fi/fv7ihjw2i65372v2sbft8/.epub?rlkey=4edhsw200b4fk064lin7wkwly&st=xsqaokbv&dl=0",
]

FALLBACK_UI_TEXTS = {
    "ONBOARDING_WELCOME": """Здесь — пауза.

Небольшие остановки
в коротких фразах, стихах,
иногда в музыке.

Ничего не нужно делать.
Можно просто быть здесь.""",
    "ONBOARDING_ASK_REMINDERS": """Иногда паузу легко почувствовать.
Иногда о ней важно вспомнить.

Нужны напоминания
об остановке?""",
    "ONBOARDING_NO_REMINDERS": """Когда возникает желание остановиться —
достаточно нажать кнопку.

Здесь появляется пауза.""",
    "ONBOARDING_ASK_FREQUENCY": "Как часто нужны напоминания?",
    "ONBOARDING_ASK_TIME": "В какое время?",
    "ONBOARDING_CONFIRM": """Пауза будет появляться
{frequency_text}
{time_text}.

В любой другой момент
пауза доступна здесь.""",
    "WELCOME_BACK": """Когда возникает желание остановиться —
достаточно нажать кнопку.""",
    "BOX_INTRO": """Следующий набор сейчас в процессе.
Он собирается внимательно и без спешки —
так, чтобы пауза в нём действительно ощущалась.

Каждый новый набор выходит первого числа месяца.
Предзаказы на него собираются до 20 числа предыдущего месяца —
это время нужно, чтобы спокойно найти
новые ароматы и вкусы,
а также подобрать предметы,
которые поддержат паузу и тишину.

Предзаказ оформляется с предоплатой —
она позволяет собрать нужное количество наборов
и сохранить ритм без спешки.

Твой следующий набор: 1 {month}.

Если этот темп откликается —
можно оставить предзаказ.""",
    "BOX_ASK_NAME": """Тебя зовут {name}?

Если да — нажми «Да, верно».
Если хочешь изменить — напиши своё имя.""",
    "BOX_ASK_PHONE": """Телефон для связи

Укажи номер в международном формате,
например: +7 999 123 45 67""",
    "BOX_ASK_ADDRESS": """Адрес доставки

Укажи полный адрес:
страна, город, улица, дом, квартира, индекс.""",
    "BOX_CONFIRM": """Проверь данные:

Имя: {name}
Телефон: {phone}
Адрес: {address}

Набор: 1 {month}
Стоимость: 79 €""",
    "BOX_PAYMENT": """Для оплаты перейди по ссылке ниже.
После оплаты нажми «Я оплатил».""",
    "BOX_THANKS": """Спасибо.

Набор будет отправлен 1 {month}
на указанный адрес.

Мы напишем, когда всё будет готово.""",
    "BOX_CONFIRMED": """Оплата подтверждена.

Набор будет отправлен 1 {month}.
Спасибо, что ты здесь.""",
    "BOX_LATER": """Хорошо.

Можно вернуться позже.""",
    "WELCOME": """Здесь — пауза

Небольшие остановки в коротких фразах, стихах, иногда в музыке.

Ничего не нужно делать.
Можно просто быть здесь.""",
    "ABOUT": """Пауза — это пространство для коротких ментальных остановок.

Тексты, видео и музыка.
Оффлайн-набор для остановок.

79 €""",
    "ORDER_START": """Оформление предзаказа

Напиши своё имя.""",
    "ORDER_EMAIL": "Теперь email — туда придёт доступ после оплаты.",
    "ORDER_CONFIRM": """Проверь данные:

Имя: {name}
Email: {email}
Сумма: 79 €

Всё верно?""",
    "ORDER_PAYMENT": """Отлично.

Для оплаты перейди по ссылке ниже.
После оплаты нажми «Я оплатил».""",
    "ORDER_THANKS": """Спасибо.

Мы проверим оплату и пришлём доступ на {email}.

Обычно это занимает несколько часов.""",
    "ORDER_CONFIRMED": """Оплата подтверждена.

Доступ отправлен на {email}.
Спасибо, что ты здесь.""",
    "HELP": """Команды:

/start — начало
/pause — получить паузу
/box — предзаказ набора""",
}

# Обязательные UI ключи для валидации
REQUIRED_UI_KEYS = [
    "ONBOARDING_WELCOME",
    "ONBOARDING_ASK_REMINDERS",
    "ONBOARDING_NO_REMINDERS",
    "ONBOARDING_ASK_FREQUENCY",
    "ONBOARDING_ASK_TIME",
    "ONBOARDING_CONFIRM",
    "WELCOME_BACK",
    "BOX_INTRO",
    "BOX_ASK_NAME",
    "BOX_ASK_PHONE",
    "BOX_ASK_ADDRESS",
    "BOX_CONFIRM",
    "BOX_PAYMENT",
    "BOX_THANKS",
    "BOX_CONFIRMED",
    "BOX_LATER",
    "WELCOME",
    "ABOUT",
    "ORDER_START",
    "ORDER_EMAIL",
    "ORDER_CONFIRM",
    "ORDER_PAYMENT",
    "ORDER_THANKS",
    "ORDER_CONFIRMED",
    "HELP",
]


class ContentManager:
    """
    Менеджер контента с in-memory кэшем.
    Fallback на hardcoded значения если БД пуста.
    """

    _instance: Optional["ContentManager"] = None

    def __init__(self):
        self._cache: dict[str, list[str]] = {}
        self._ui_cache: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._loaded = False

    @classmethod
    def get_instance(cls) -> "ContentManager":
        """Получить singleton instance."""
        if cls._instance is None:
            cls._instance = ContentManager()
        return cls._instance

    async def reload(self) -> None:
        """
        Атомарная перезагрузка кэша из SQLite.
        Вызывается при старте и после /sync.
        """
        async with self._lock:
            new_cache: dict[str, list[str]] = {}
            new_ui_cache: dict[str, str] = {}

            try:
                async with get_session() as session:
                    # Загружаем контент
                    result = await session.execute(
                        select(ContentCache).where(ContentCache.is_active == True)
                    )
                    entries = result.scalars().all()

                    for entry in entries:
                        if entry.content_type not in new_cache:
                            new_cache[entry.content_type] = []
                        new_cache[entry.content_type].append(entry.content)

                    # Загружаем UI тексты
                    ui_result = await session.execute(select(UITextCache))
                    ui_entries = ui_result.scalars().all()

                    for entry in ui_entries:
                        new_ui_cache[entry.key] = entry.text

                logger.info(
                    f"Content cache loaded: {sum(len(v) for v in new_cache.values())} items, "
                    f"{len(new_ui_cache)} UI texts"
                )

            except Exception as e:
                logger.warning(f"Failed to load cache from DB: {e}, using fallback")

            self._cache = new_cache
            self._ui_cache = new_ui_cache
            self._loaded = True

    def validate_ui_keys(self) -> list[str]:
        """
        Проверить наличие всех обязательных UI ключей.

        Returns:
            Список отсутствующих ключей
        """
        missing = []
        for key in REQUIRED_UI_KEYS:
            if key not in self._ui_cache:
                missing.append(key)
        return missing

    # ===== КОНТЕНТ =====

    async def get_random_pause_short(self) -> str:
        """Случайная короткая пауза."""
        return await self._get_random_content("pause_short", FALLBACK_PAUSE_SHORT)

    async def get_random_pause_long(self) -> str:
        """Случайная длинная пауза."""
        return await self._get_random_content("pause_long", FALLBACK_PAUSE_LONG)

    async def get_random_breathe(self) -> str:
        """Случайная медитация."""
        return await self._get_random_content("breathe", FALLBACK_BREATHE)

    async def get_random_movie(self) -> str:
        """Случайный фильм."""
        return await self._get_random_content("movie", FALLBACK_MOVIES)

    async def get_random_book(self) -> str:
        """Случайная книга."""
        return await self._get_random_content("book", FALLBACK_BOOKS)

    async def _get_random_content(self, content_type: str, fallback: list[str]) -> str:
        """Получить случайный контент с fallback."""
        if not self._loaded:
            await self.reload()

        async with self._lock:
            items = self._cache.get(content_type, [])

        if not items:
            logger.debug(f"No cached content for {content_type}, using fallback")
            items = fallback

        return random.choice(items)

    # ===== UI ТЕКСТЫ =====

    async def get_ui_text(self, key: str, fallback: str = "", **kwargs) -> str:
        """
        Получить UI текст по ключу.
        Поддерживает форматирование: get_ui_text("KEY", name="John")

        Args:
            key: Ключ текста (например ONBOARDING_WELCOME)
            fallback: Fallback значение если ключ не найден
            **kwargs: Параметры для форматирования

        Returns:
            Отформатированный текст
        """
        if not self._loaded:
            await self.reload()

        async with self._lock:
            text = self._ui_cache.get(key)

        if text is None:
            # Пробуем fallback из словаря
            text = FALLBACK_UI_TEXTS.get(key)
            if text is None:
                logger.warning(f"UI text not found: {key}")
                text = fallback or f"[{key}]"

        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError as e:
                logger.error(f"Missing placeholder in {key}: {e}")

        return text
