# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot for selling "Пауза" (Pause) — a product offering short mental break content. Built with aiogram 3.x (async Python Telegram framework) and SQLAlchemy 2.x async ORM.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

Required environment variables: `BOT_TOKEN`, `ADMIN_ID`, `PAYMENT_LINK`

## Architecture

**Entry point**: `main.py` — initializes database, creates Bot/Dispatcher, registers routers

**Configuration**: `config.py` — dataclass-based config loaded from environment variables

**Handlers** (aiogram Router pattern):
- `handlers/base.py` — user commands (`/start`, `/about`, `/help`) and navigation callbacks
- `handlers/orders.py` — order flow using FSM (Finite State Machine) with `OrderForm` states
- `handlers/admin.py` — admin commands (`/orders`, `/stats`) and order confirmation callbacks

**Database** (async SQLAlchemy):
- `database/connection.py` — engine and session factory (currently hardcoded to SQLite)
- `database/models.py` — `User`, `Order` (with `OrderStatus` enum), `Reminder` models

**UI**:
- `texts.py` — all bot messages (Russian)
- `keyboards.py` — inline keyboard builders using `InlineKeyboardBuilder`

## Key Patterns

- Config is passed to handlers via `dp["config"] = config` and received as `config: Config` parameter
- All database operations use async context manager: `async with get_session() as session:`
- Order flow uses aiogram FSM: states defined in `OrderForm(StatesGroup)`, transitions via `state.set_state()`
- Admin callbacks use prefix pattern: `confirm_{order_id}`, `reject_{order_id}`
