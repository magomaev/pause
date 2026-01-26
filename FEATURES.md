# Функционал бота "Пауза"

Этот документ — источник правды о функционале бота. Агент должен сверяться с ним при любых изменениях.

---

## КРИТИЧЕСКИЕ ПРАВИЛА ДЛЯ АГЕНТА

1. **НЕ удалять фичи** без явного запроса пользователя
2. **НЕ менять логику** существующих фич без необходимости
3. **НЕ менять порядок роутеров** — menu_router ВСЕГДА последний
4. При изменении одной фичи — проверить, что не сломались другие
5. При добавлении нового роутера — добавить его ПЕРЕД menu_router

---

## 1. Архитектура и роутеры

### Структура проекта
```
pause/
├── main.py              # Точка входа
├── config.py            # Конфигурация (dataclass)
├── texts.py             # Все тексты сообщений
├── keyboards.py         # Конструкторы клавиатур
├── content.py           # ContentManager (singleton)
├── middleware.py        # Rate limiting middleware
├── scheduler.py         # Планировщик напоминаний
├── notion_sync.py       # Синхронизация с Notion
├── handlers/
│   ├── onboarding.py    # /start, /help, онбординг FSM
│   ├── pause.py         # /pause
│   ├── box.py           # Предзаказ набора FSM
│   ├── orders.py        # Заказы FSM
│   ├── admin.py         # Админ команды
│   └── menu.py          # Reply keyboard + catch-all
└── database/
    ├── connection.py    # Подключение к БД
    └── models.py        # SQLAlchemy модели
```

### Порядок регистрации роутеров (КРИТИЧНО!)

```python
# main.py — порядок ВАЖЕН!
dp.include_router(onboarding_router)  # 1. /start, /help
dp.include_router(pause_router)       # 2. /pause
dp.include_router(box_router)         # 3. Предзаказ набора
dp.include_router(orders_router)      # 4. Заказы
dp.include_router(admin_router)       # 5. Админ
dp.include_router(menu_router)        # 6. ПОСЛЕДНИЙ — catch-all!
```

**Почему порядок важен:** `menu_router` содержит catch-all обработчик для необработанных сообщений. Если его поставить раньше — он перехватит все сообщения.

---

## 2. Команды бота

| Команда | Описание | Роутер |
|---------|----------|--------|
| `/start` | Онбординг или welcome | onboarding_router |
| `/help` | Справка | onboarding_router |
| `/pause` | Случайная пауза | pause_router |
| `/box` | Предзаказ набора | box_router |
| `/breathe` | Медитация | menu_router |
| `/movie` | Фильм | menu_router |
| `/book` | Книга | menu_router |
| `/settings` | Настройки напоминаний | menu_router |
| `/cancel` | Отмена текущего действия | onboarding_router |
| `/orders` | Список заказов (админ) | admin_router |
| `/stats` | Статистика (админ) | admin_router |
| `/sync` | Синхронизация с Notion (админ) | admin_router |

---

## 3. Reply Keyboard (постоянное меню)

Сетка 2x2 внизу экрана:

```
[Пауза]         [Длинная пауза]
[Новый набор]   [Напоминания]
```

| Кнопка | Константа | Действие |
|--------|-----------|----------|
| Пауза | `BTN_MENU_PAUSE` | Случайная пауза с чередованием типов |
| Длинная пауза | `BTN_MENU_LONG_PAUSE` | Медитация/фильм/книга с чередованием |
| Новый набор | `BTN_MENU_NEW_BOX` | Переход к /box |
| Напоминания | `BTN_MENU_REMINDERS` | Настройки напоминаний |

---

## 4. Онбординг

### FSM состояния (OnboardingForm)
```
/start → reminder_choice → frequency → time → завершение
```

### Логика
1. `/start` — если `onboarding_completed=False`, начинаем онбординг
2. Спрашиваем: "Нужны напоминания?" (да/нет)
3. Если "да" → частота (ежедневно / 3 раза в неделю / раз в неделю)
4. Если "да" → время (утро / день / вечер / случайно)
5. Сохраняем в User:
   - `onboarding_completed = True`
   - `reminder_enabled = True/False`
   - `reminder_frequency` (если enabled)
   - `reminder_time` (если enabled)

### Callbacks
- `reminders_yes` / `reminders_no`
- `freq_daily` / `freq_3_per_week` / `freq_weekly`
- `time_morning` / `time_afternoon` / `time_evening` / `time_random`

---

## 5. Паузы

### Типы контента
- **Короткая пауза:** стихи (`pause_poems`) ↔ музыка (`pause_music`)
- **Длинная пауза:** медитация → фильм → книга (цикл)

### Циклическое чередование типов

```python
# Логика в handlers/menu.py и handlers/pause.py
# Отслеживаем last_pause_type в FSM state

async def get_pause_with_rotation(state: FSMContext):
    data = await state.get_data()
    last_type = data.get("last_pause_type")

    # Получаем паузу, исключая предыдущий тип
    content, content_type = content_manager.get_random_pause_excluding(last_type)

    # Сохраняем текущий тип для следующего раза
    await state.update_data(last_pause_type=content_type)
    return content
```

### Важно
- `last_pause_type` — для коротких пауз (стихи/музыка)
- `last_long_pause_type` — для длинных пауз (медитация/фильм/книга)

---

## 6. Предзаказ набора (BoxOrder)

### FSM состояния (BoxOrderForm)
```
/box → box_start → name → contact → address → confirm → payment
```

### Логика создания заказа
```python
# handlers/box.py — заказ создается СРАЗУ при box_start
@router.callback_query(F.data == "box_start")
async def box_start(callback: CallbackQuery, state: FSMContext):
    # 1. Создаем BoxOrder в БД со статусом PENDING
    order = BoxOrder(
        telegram_id=callback.from_user.id,
        box_month=calculate_box_month(),  # Автоматический расчет
        status=BoxOrderStatus.PENDING
    )
    session.add(order)
    await session.commit()

    # 2. Сохраняем order_id в FSM для последующего обновления
    await state.update_data(order_id=order.id)

    # 3. Переходим к вводу имени
    await state.set_state(BoxOrderForm.name)
```

### Расчет месяца набора
```python
def calculate_box_month():
    today = datetime.now()
    if today.day <= 20:
        # До 20 числа → набор следующего месяца
        target = today.replace(day=1) + timedelta(days=32)
    else:
        # После 20 → набор через месяц
        target = today.replace(day=1) + timedelta(days=62)
    return target.strftime("%Y-%m")  # Формат: "2026-02"
```

### Статусы BoxOrderStatus
- `PENDING` — создан, ожидает оплаты
- `PAID` — пользователь нажал "Я оплатил"
- `CONFIRMED` — админ подтвердил
- `SHIPPED` — отправлен
- `DELIVERED` — доставлен
- `CANCELLED` — отменен

### Callbacks
- `box_start` — начало оформления
- `box_name_ok` — подтверждение имени из Telegram
- `box_confirm` — подтверждение данных
- `box_paid` — отметка об оплате
- `box_later` — вернуться позже
- `box_cancel` — отмена

---

## 7. Заказы (Order)

### FSM состояния (OrderForm)
```
order → name → contact → address → confirm → payment
```

### Отличие от BoxOrder
- Заказ создается при `confirm_order`, а не в начале
- Нет поля `box_month`
- Используется для цифрового продукта

### Статусы OrderStatus
- `PENDING` — создан, ожидает оплаты
- `PAID` — пользователь отметил оплату
- `CONFIRMED` — админ подтвердил
- `CANCELLED` — отменен

### Callbacks
- `order` — начало оформления
- `confirm_order` — подтверждение данных
- `i_paid` — отметка об оплате
- `cancel_order` — отмена

---

## 8. Админ функционал

### Команды (только для admin_id)

| Команда | Описание |
|---------|----------|
| `/orders` | Последние 10 заказов |
| `/stats` | Статистика (пользователи, заказы, выручка) |
| `/sync` | Синхронизация контента с Notion |

### Callbacks для подтверждения

```python
# Order (цифровой продукт)
confirm_{order_id}   # → статус CONFIRMED
reject_{order_id}    # → статус CANCELLED

# BoxOrder (физический набор)
box_confirm_{order_id}  # → статус CONFIRMED
box_reject_{order_id}   # → статус CANCELLED
```

### Уведомления админу
При каждом заказе/оплате админ получает сообщение с кнопками "Подтвердить" / "Отклонить".

---

## 9. Модели БД

### User
```python
class User:
    id: int                           # PK
    telegram_id: int                  # Уникальный ID Telegram
    username: str | None              # @username
    first_name: str | None            # Имя из Telegram
    created_at: datetime              # Дата регистрации
    onboarding_completed: bool        # Пройден ли онбординг
    reminder_enabled: bool            # Включены ли напоминания
    reminder_frequency: ReminderFrequency | None  # DAILY / THREE_PER_WEEK / WEEKLY
    reminder_time: ReminderTime | None            # MORNING / AFTERNOON / EVENING / RANDOM
```

### Order
```python
class Order:
    id: int
    telegram_id: int
    name: str
    phone: str                        # Контакт (telegram/whatsapp/телефон)
    address: str
    email: str | None                 # Deprecated
    amount: int = 79
    currency: str = "EUR"
    status: OrderStatus               # PENDING / PAID / CONFIRMED / CANCELLED
    created_at: datetime
    paid_at: datetime | None
    confirmed_at: datetime | None
```

### BoxOrder
```python
class BoxOrder:
    id: int
    telegram_id: int
    name: str | None
    phone: str | None                 # Контакт
    email: str | None
    address: str | None               # Полный адрес доставки
    box_month: str                    # Формат "2026-02"
    amount: int = 79
    currency: str = "EUR"
    status: BoxOrderStatus            # PENDING / PAID / CONFIRMED / SHIPPED / DELIVERED / CANCELLED
    created_at: datetime
    paid_at: datetime | None
    shipped_at: datetime | None
```

### Reminder
```python
class Reminder:
    id: int
    text: str | None
    media_type: str | None            # photo / video / audio
    media_file_id: str | None
    scheduled_at: datetime
    sent: bool
    target: str                       # all / paid / telegram_id
    created_at: datetime
```

### ContentCache / UITextCache
Кэш контента и UI текстов из Notion.

---

## 10. ContentManager

Singleton для управления контентом.

### Методы получения контента
```python
get_random_pause()                    # Случайная пауза (стихи/музыка)
get_random_pause_excluding(type)      # С исключением типа (для чередования)
get_random_long_pause()               # Длинная пауза (медитация/фильм/книга)
get_random_long_pause_excluding(type) # С исключением типа
get_random_reminder()                 # Короткая фраза для напоминания
get_random_breathe()                  # Медитация
get_random_movie()                    # Фильм
get_random_book()                     # Книга
```

### Методы UI текстов
```python
reload()                              # Загрузка кэша из SQLite
validate_ui_keys()                    # Проверка обязательных ключей
get_ui_text(key, **kwargs)            # Получение текста с форматированием
```

---

## 11. Валидация

| Поле | Правила |
|------|---------|
| Имя | 2-100 символов |
| Контакт | Минимум 3 символа |
| Адрес (BoxOrder) | 20-500 символов |
| Адрес (Order) | Минимум 10 символов |

---

## 12. Переменные окружения

| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | Да |
| `ADMIN_ID` | ID администратора | Да |
| `PAYMENT_LINK` | Ссылка на оплату (Revolut) | Да |
| `DATABASE_URL` | URL базы данных | Нет (default: sqlite) |
| `NOTION_TOKEN` | Токен Notion API | Нет |
| `NOTION_CONTENT_DB` | ID базы контента Notion | Нет |
| `NOTION_UI_TEXTS_DB` | ID базы UI текстов Notion | Нет |
