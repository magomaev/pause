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
python main.py
```

## Переменные окружения

Обязательные: `BOT_TOKEN`, `ADMIN_ID`, `PAYMENT_LINK`

Опциональные: `DATABASE_URL`, `NOTION_TOKEN`, `NOTION_CONTENT_DB`, `NOTION_UI_TEXTS_DB`

## Архитектура

```
pause/
├── main.py              # Точка входа
├── config.py            # Конфигурация
├── texts.py             # Тексты сообщений
├── keyboards.py         # Клавиатуры
├── content.py           # ContentManager (singleton)
├── middleware.py        # Rate limiting middleware
├── scheduler.py         # Планировщик напоминаний
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

## Основные фичи (см. FEATURES.md)

- Онбординг с настройкой напоминаний
- Короткие паузы (стихи/музыка с чередованием)
- Длинные паузы (медитация/фильм/книга с чередованием)
- Предзаказ физического набора (BoxOrder)
- Заказы цифрового продукта (Order)
- Админ: подтверждение заказов, статистика, синхронизация с Notion
