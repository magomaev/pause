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

# Короткие фразы — только для напоминаний
FALLBACK_PAUSE_PHRASES = [
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

# Музыка — для кнопки "Пауза"
FALLBACK_PAUSE_MUSIC = [
    "https://youtu.be/YvAq6D3jHnY?si=OY1Gg7VbR5yu9D8r",
    "https://youtu.be/8YTHFnv-eV0?si=Uo4SWRA3s_Y1H_8e",
    "https://youtu.be/gnhJ4Ceor_M?si=jSyV0TM7gwjNxi6e",
    "https://youtu.be/ycYN0IXA-4U?si=rT9mg36Pzxqr53mv",
    "https://youtu.be/Q0d7ATDFZx0?si=sDOc0ZMnwD7Uw2Uo",
    "https://youtu.be/84D_J05McA0?si=MQlCYJWbS3ji8FgJ",
    "https://youtu.be/VNLrCWCv38Y?si=bqZaBhS7H98UgZUC",
    "https://youtu.be/xN-fUozKM0k?si=MoZKMq6HaF_-sbYT",
    "https://youtu.be/htQBS2Ikz6c?si=n0_OBV124kze1xyO",
    "https://youtu.be/StWFJumEF7I?si=6svKGR2hhKh0-RVy",
]

# Стихи — для кнопки "Пауза"
FALLBACK_PAUSE_POEMS = [
    """О счастье мы всегда лишь вспоминаем.
А счастье всюду. Может быть, оно —
Вот этот сад осенний за сараем
И чистый воздух, льющийся в окно.

В бездонном небе лёгким белым краем
Встаёт, сияет облако. Давно
Слежу за ним… Мы мало видим, знаем,
А счастье только знающим дано.

Иван Бунин""",
    """Я не люблю фатального исхода,
От жизни никогда не устаю.
Я не люблю любое время года,
Когда веселых песен не пою.

Я не люблю холодного цинизма,
В восторженность не верю, и еще —
Когда чужой мои читает письма,
Заглядывая мне через плечо.

Я не люблю, когда наполовину
Или когда прервали разговор.
Я не люблю, когда стреляют в спину,
Я также против выстрелов в упор.

Я ненавижу сплетни в виде версий,
Червей сомненья, почестей иглу,
Или — когда все время против шерсти,
Или — когда железом по стеклу.

Я не люблю уверенности сытой,
Уж лучше пусть откажут тормоза!
Досадно мне, что слово «честь» забыто,
И что в чести наветы за глаза.

Когда я вижу сломанные крылья —
Нет жалости во мне и неспроста.
Я не люблю насилье и бессилье,
Вот только жаль распятого Христа.

Я не люблю себя, когда я трушу,
Обидно мне, когда невинных бьют,
Я не люблю, когда мне лезут в душу,
Тем более, когда в нее плюют.

Я не люблю манежи и арены,
На них мильон меняют по рублю,
Пусть впереди большие перемены,
Я это никогда не полюблю.

Владимир Высоцкий""",
    """все важные фразы должны быть тихими,
все фото с родными всегда нерезкие.
самые странные люди всегда великие,
а причины для счастья всегда невеские.

самое честное слышишь на кухне ночью,
ведь если о чувствах — не по телефону,
а если уж плакать, так выть по-волчьи,
чтоб тоскливым эхом на полрайона.

любимые песни — все хриплым голосом,
все стихи любимые — неизвестные.
все наглые люди всегда ничтожества,
а все близкие люди всегда не местные.

все важные встречи всегда случайные.
самые верные подданные — предатели,
цирковые клоуны — все печальные,
а упрямые скептики — все мечтатели.

если дом уютный — не замок точно,
а квартирка старенькая в Одессе.
если с кем связаться — навеки, прочно.
пусть сейчас не так всё, но ты надейся.

да, сейчас иначе, но верь: мы сбудемся,
если уж менять, так всю жизнь по-новому.
то, что самое важное, не забудется,
гениальные мысли всегда бредовые.

кто ненужных вычеркнул, те свободные,
нужно отпускать, с кем вы слишком разные.
ведь, если настроение не новогоднее,
значит точно не с теми празднуешь.""",
    """Когда мне встречается в людях дурное,
То долгое время я верить стараюсь,
Что это скорее всего напускное,
Что это случайность. И я ошибаюсь.

И, мыслям подобным ища подтвержденья,
Стремлюсь я поверить, забыв про укор,
Что лжец, может, просто большой фантазёр,
А хам, он, наверно, такой от смущенья.

Что сплетник, шагнувший ко мне на порог,
Возможно, по глупости разболтался,
А друг, что однажды в беде не помог,
Не предал, а просто тогда растерялся.

Я вовсе не прячусь от бед под крыло.
Иными тут мерками следует мерить.
Ужасно не хочется верить во зло,
И в подлость ужасно не хочется верить!

Поэтому, встретив нечестных и злых,
Нередко стараешься волей-неволей
В душе своей словно бы выправить их
И попросту «отредактировать», что ли!

Но факты и время отнюдь не пустяк.
И сколько порой ни насилуешь душу,
А гниль всё равно невозможно никак
Ни спрятать, ни скрыть, как ослиные уши.

Ведь злого, признаться, мне в жизни моей
Не так уж и мало встречать доводилось.
И сколько хороших надежд поразбилось,
И сколько вот так потерял я друзей!

И всё же, и всё же я верить не брошу,
Что надо в начале любого пути
С хорошей, с хорошей и только с хорошей,
С доверчивой меркою к людям идти!

Пусть будут ошибки (такое не просто),
Но как же ты будешь безудержно рад,
Когда эта мерка придётся по росту
Тому, с кем ты станешь богаче стократ!

Пусть циники жалко бормочут, как дети,
Что, дескать, непрочная штука — сердца...
Не верю! Живут, существуют на свете
И дружба навек, и любовь до конца!

И сердце твердит мне: ищи же и действуй.
Но только одно не забудь наперёд:
Ты сам своей мерке большой соответствуй,
И всё остальное, увидишь, — придёт!

Эдуард Асадов""",
    """ОНА:

Когда мне будет восемьдесят пять,
Когда начну я тапочки терять,
В бульоне размягчать кусочки хлеба,
Вязать излишне длинные шарфы,
Ходить, держась за стены и шкафы,
И долго-долго вглядываться в небо,

Когда все женское,
Что мне сейчас дано,
Истратится и станет все равно —
Уснуть, проснуться, или не проснуться.
Из виданного на своем веку
Я бережно твой образ извлеку,
И чуть заметно губы улыбнутся.

ОН:

Когда мне будет восемьдесят пять,
По дому буду твои тапочки искать,
Ворчать на то, что трудно мне сгибаться,
Носить какие-то нелепые шарфы
Из тех, что для меня связала ты.

А утром, просыпаясь до рассвета,
Прислушаюсь к дыханью твоему,
Вдруг улыбнусь и тихо обниму.

Когда мне будет восемьдесят пять,
С тебя пылинки буду я сдувать,
Твои седые букли поправлять
И, взявшись за руки, по скверику гулять.

И нам не страшно будет умирать,
Когда нам будет восемьдесят пять…

Эдуард Асадов""",
]

FALLBACK_BREATHE = [
    "https://soundcloud.com/aleksandra-ermolenko/pauza-dekabr?in=aleksandra-ermolenko%2Fsets%2Fpauza&si=a3094c0bc9f84f0fbad941be6fbdd883&utm_source=clipboard&utm_medium=text&utm_campaign=social_sharing",
]

FALLBACK_MOVIES = [
    "https://www.imdb.com/title/tt5247022",
    "https://www.imdb.com/title/tt1626146",
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

    async def get_random_pause(self) -> str:
        """Кнопка 'Пауза', /pause, pause_now — стихи + музыка."""
        all_content: list[str] = []

        if not self._loaded:
            await self.reload()

        async with self._lock:
            # Из кэша: стихи (pause_long) + музыка (pause_music)
            all_content.extend(self._cache.get("pause_long", []))
            all_content.extend(self._cache.get("pause_music", []))

        # Если кэш пуст — используем fallback
        if not all_content:
            all_content = FALLBACK_PAUSE_POEMS + FALLBACK_PAUSE_MUSIC

        return random.choice(all_content)

    async def get_random_long_pause(self) -> str:
        """Кнопка 'Длинная пауза' — медитация + фильмы + книги."""
        all_content: list[str] = []

        if not self._loaded:
            await self.reload()

        async with self._lock:
            for content_type in ["breathe", "movie", "book"]:
                all_content.extend(self._cache.get(content_type, []))

        # Если кэш пуст — используем fallback
        if not all_content:
            all_content = FALLBACK_BREATHE + FALLBACK_MOVIES + FALLBACK_BOOKS

        return random.choice(all_content)

    async def get_random_reminder(self) -> str:
        """Напоминания — только короткие фразы."""
        return await self._get_random_content("pause_phrases", FALLBACK_PAUSE_PHRASES)

    async def get_random_breathe(self) -> str:
        """Случайная медитация (для /breathe)."""
        return await self._get_random_content("breathe", FALLBACK_BREATHE)

    async def get_random_movie(self) -> str:
        """Случайный фильм (для /movie)."""
        return await self._get_random_content("movie", FALLBACK_MOVIES)

    async def get_random_book(self) -> str:
        """Случайная книга (для /book)."""
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
