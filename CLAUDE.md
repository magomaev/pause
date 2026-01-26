# CLAUDE.md

## ПЕРЕД ИЗМЕНЕНИЯМИ — ЧИТАЙ FEATURES.md

**Полное описание функционала:** см. `FEATURES.md`

### Правила для агента:
1. **НЕ удалять фичи** без явного запроса пользователя
2. **НЕ менять логику** существующих фич без необходимости
3. **НЕ менять порядок роутеров** — menu_router ВСЕГДА последний
4. При изменении — проверить, что не сломались другие фичи

---

## Описание проекта

Telegram бот для продажи "Пауза" — продукт с контентом для ментальных пауз. Построен на aiogram 3.x и SQLAlchemy 2.x async.

## Команды

```bash
pip install -r requirements.txt

# Управление ботом (рекомендуется)
./bot.sh start    # Запуск
./bot.sh stop     # Остановка
./bot.sh restart  # Перезапуск
./bot.sh status   # Проверка статуса

# Или напрямую (не рекомендуется — может накапливать процессы)
python main.py
```

**Важно:** Не запускать бота напрямую через `python main.py &` — это приводит к накоплению процессов и TelegramConflictError. Использовать `./bot.sh`.

## Переменные окружения

Обязательные: `BOT_TOKEN`, `ADMIN_ID`, `PAYMENT_LINK`

Опциональные:
- `DATABASE_URL` — URL базы данных (default: sqlite)
- `NOTION_TOKEN`, `NOTION_CONTENT_DB`, `NOTION_UI_TEXTS_DB` — интеграция с Notion
- `WELCOME_PHOTO_PATH` — путь к welcome-картинке (например, `assets/welcome.jpg`)

## Архитектура

```
pause/
├── main.py              # Точка входа
├── bot.sh               # Скрипт управления ботом (start/stop/restart/status)
├── config.py            # Конфигурация
├── texts.py             # Тексты сообщений
├── keyboards.py         # Клавиатуры
├── content.py           # ContentManager (singleton)
├── middleware.py        # Rate limiting middleware
├── scheduler.py         # Планировщик напоминаний
├── assets/              # Медиа файлы
│   └── welcome.jpg      # Welcome-картинка для онбординга
├── handlers/
│   ├── onboarding.py    # /start, /help, онбординг
│   ├── pause.py         # /pause
│   ├── box.py           # Предзаказ набора
│   ├── orders.py        # Заказы
│   ├── admin.py         # Админ команды
│   └── menu.py          # Reply keyboard + catch-all
└── database/
    ├── connection.py
    └── models.py
```

## Порядок роутеров (КРИТИЧНО!)

```python
dp.include_router(onboarding_router)  # 1
dp.include_router(pause_router)       # 2
dp.include_router(box_router)         # 3
dp.include_router(orders_router)      # 4
dp.include_router(admin_router)       # 5
dp.include_router(menu_router)        # 6 — ПОСЛЕДНИЙ!
```

**menu_router содержит catch-all** — если поставить раньше, перехватит все сообщения.

## Ключевые паттерны

- Config через `dp["config"]`, получается как `config: Config` в handlers
- Async sessions: `async with get_session() as session:`
- FSM для многошаговых процессов (онбординг, заказы)
- Admin callbacks: `confirm_{id}`, `reject_{id}`, `box_confirm_{id}`, `box_reject_{id}`
- Циклическое чередование контента через `last_pause_type` в FSM state

## Работа с медиа (изображения)

Используем `FSInputFile` для отправки локальных файлов (не file_id):

```python
from aiogram.types import FSInputFile
from pathlib import Path

if config.welcome_photo_path:
    photo_path = Path(config.welcome_photo_path)
    if photo_path.exists():
        photo = FSInputFile(photo_path)
        await message.answer_photo(photo=photo, caption=text)
```

**Почему FSInputFile, а не file_id:**
- Надёжнее — не зависит от Telegram серверов
- Портативно — работает при смене токена бота
- Версионируется — файл в репозитории

Медиа файлы хранятся в `assets/`.

## Основные фичи (см. FEATURES.md)

- Онбординг с настройкой напоминаний
- Короткие паузы (стихи/музыка с чередованием)
- Длинные паузы (медитация/фильм/книга с чередованием)
- Предзаказ физического набора (BoxOrder)
- Заказы цифрового продукта (Order)
- Админ: подтверждение заказов, статистика, синхронизация с Notion

## Типичные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `TelegramConflictError` | Несколько инстансов бота | `./bot.sh stop` затем `./bot.sh start` |
| `relationship('List[Order]')` | Устаревший синтаксис SQLAlchemy | Использовать `list["Order"]` вместо `"List[Order]"` |
| Фото не отправляется | Файл не найден или неверный путь | Проверить `WELCOME_PHOTO_PATH` и наличие файла в `assets/` |
