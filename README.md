# Пауза — Telegram Bot

Бот для продажи продукта "Пауза" — пространства для коротких ментальных остановок.

## Возможности

- Информация о продукте
- Оформление предзаказа
- Оплата через Revolut Payment Link
- Уведомления админу о заказах
- Подтверждение оплаты

## Быстрый старт

### 1. Установка

```bash
# Клонируй репозиторий
git clone <repo-url>
cd pause-bot

# Создай виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установи зависимости
pip install -r requirements.txt
```

### 2. Настройка

```bash
# Скопируй пример конфига
cp .env.example .env

# Отредактируй .env
nano .env
```

Заполни:
- `BOT_TOKEN` — токен от @BotFather
- `ADMIN_ID` — твой Telegram ID (узнать: @userinfobot)
- `PAYMENT_LINK` — ссылка из Revolut Pro

### 3. Запуск

```bash
python main.py
```

## Команды бота

**Для пользователей:**
- `/start` — начало
- `/about` — о продукте
- `/help` — справка

**Для админа:**
- `/orders` — список заказов
- `/stats` — статистика

## Деплой на Railway

1. Создай аккаунт на [railway.app](https://railway.app)
2. Подключи GitHub репозиторий
3. Добавь переменные окружения (BOT_TOKEN, ADMIN_ID, PAYMENT_LINK)
4. Добавь PostgreSQL из маркетплейса
5. Railway автоматически задеплоит

## Структура

```
pause-bot/
├── main.py              # Точка входа
├── config.py            # Конфигурация
├── texts.py             # Все тексты бота
├── keyboards.py         # Клавиатуры
├── handlers/
│   ├── base.py          # Основные команды
│   ├── orders.py        # Заказы
│   └── admin.py         # Админка
├── database/
│   ├── models.py        # Модели
│   └── connection.py    # Подключение
├── requirements.txt
└── .env.example
```
