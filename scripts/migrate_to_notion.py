#!/usr/bin/env python3
"""
Миграция контента из texts.py в Notion.

Использование:
1. Создай Notion Integration на https://www.notion.so/my-integrations
2. Создай 2 базы данных в Notion (Content и UI Texts) с нужными колонками
3. Расшарь базы интеграции (Share → Invite → выбери интеграцию)
4. Заполни переменные ниже
5. Запусти: python scripts/migrate_to_notion.py

Структура базы "Content":
- Title (title): название записи
- Type (select): pause_short, pause_long, breathe, movie, book
- Content (rich_text): текст или URL
- Active (checkbox): true

Структура базы "UI Texts":
- Key (title): ключ текста (ONBOARDING_WELCOME)
- Category (select): onboarding, box, order, system
- Text (rich_text): текст с {placeholders}
"""
import asyncio
import os
import sys

import httpx

# ===== НАСТРОЙКИ (заполни перед запуском) =====
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
CONTENT_DB_ID = os.getenv("NOTION_CONTENT_DB", "")
UI_TEXTS_DB_ID = os.getenv("NOTION_UI_TEXTS_DB", "")

# Добавляем родительскую директорию в path для импорта texts
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import texts


async def create_page(client: httpx.AsyncClient, database_id: str, properties: dict) -> dict:
    """Создать страницу в Notion."""
    response = await client.post(
        "/pages",
        json={
            "parent": {"database_id": database_id},
            "properties": properties,
        },
    )
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        response.raise_for_status()
    return response.json()


def make_title(text: str) -> dict:
    """Создать Title property."""
    return {"title": [{"text": {"content": text}}]}


def make_rich_text(text: str) -> dict:
    """Создать Rich Text property."""
    # Notion имеет лимит 2000 символов на блок
    if len(text) <= 2000:
        return {"rich_text": [{"text": {"content": text}}]}

    # Разбиваем на блоки
    blocks = []
    for i in range(0, len(text), 2000):
        blocks.append({"text": {"content": text[i : i + 2000]}})
    return {"rich_text": blocks}


def make_select(value: str) -> dict:
    """Создать Select property."""
    return {"select": {"name": value}}


def make_checkbox(value: bool) -> dict:
    """Создать Checkbox property."""
    return {"checkbox": value}


async def migrate_content(client: httpx.AsyncClient):
    """Миграция контента (паузы, ссылки)."""
    print("\n=== Миграция контента ===")

    # PAUSE_SHORT
    for i, text in enumerate(texts.PAUSE_SHORT, 1):
        props = {
            "Title": make_title(f"pause_short_{i}"),
            "Type": make_select("pause_short"),
            "Content": make_rich_text(text),
            "Active": make_checkbox(True),
        }
        await create_page(client, CONTENT_DB_ID, props)
        print(f"  pause_short_{i}")
        await asyncio.sleep(0.35)  # Rate limit: 3 req/sec

    # PAUSE_LONG
    for i, text in enumerate(texts.PAUSE_LONG, 1):
        props = {
            "Title": make_title(f"pause_long_{i}"),
            "Type": make_select("pause_long"),
            "Content": make_rich_text(text),
            "Active": make_checkbox(True),
        }
        await create_page(client, CONTENT_DB_ID, props)
        print(f"  pause_long_{i}")
        await asyncio.sleep(0.35)

    # BREATHE_CONTENT
    for i, url in enumerate(texts.BREATHE_CONTENT, 1):
        props = {
            "Title": make_title(f"breathe_{i}"),
            "Type": make_select("breathe"),
            "Content": make_rich_text(url),
            "Active": make_checkbox(True),
        }
        await create_page(client, CONTENT_DB_ID, props)
        print(f"  breathe_{i}")
        await asyncio.sleep(0.35)

    # MOVIES
    for i, url in enumerate(texts.MOVIES, 1):
        props = {
            "Title": make_title(f"movie_{i}"),
            "Type": make_select("movie"),
            "Content": make_rich_text(url),
            "Active": make_checkbox(True),
        }
        await create_page(client, CONTENT_DB_ID, props)
        print(f"  movie_{i}")
        await asyncio.sleep(0.35)

    # BOOKS
    for i, url in enumerate(texts.BOOKS, 1):
        props = {
            "Title": make_title(f"book_{i}"),
            "Type": make_select("book"),
            "Content": make_rich_text(url),
            "Active": make_checkbox(True),
        }
        await create_page(client, CONTENT_DB_ID, props)
        print(f"  book_{i}")
        await asyncio.sleep(0.35)

    print("Контент мигрирован!")


async def migrate_ui_texts(client: httpx.AsyncClient):
    """Миграция UI текстов."""
    print("\n=== Миграция UI текстов ===")

    ui_texts = {
        # Онбординг
        "ONBOARDING_WELCOME": ("onboarding", texts.ONBOARDING_WELCOME),
        "ONBOARDING_ASK_REMINDERS": ("onboarding", texts.ONBOARDING_ASK_REMINDERS),
        "ONBOARDING_NO_REMINDERS": ("onboarding", texts.ONBOARDING_NO_REMINDERS),
        "ONBOARDING_ASK_FREQUENCY": ("onboarding", texts.ONBOARDING_ASK_FREQUENCY),
        "ONBOARDING_ASK_TIME": ("onboarding", texts.ONBOARDING_ASK_TIME),
        "ONBOARDING_CONFIRM": ("onboarding", texts.ONBOARDING_CONFIRM),
        "WELCOME_BACK": ("onboarding", texts.WELCOME_BACK),
        # Набор
        "BOX_INTRO": ("box", texts.BOX_INTRO),
        "BOX_ASK_NAME": ("box", texts.BOX_ASK_NAME),
        "BOX_ASK_PHONE": ("box", texts.BOX_ASK_PHONE),
        "BOX_ASK_ADDRESS": ("box", texts.BOX_ASK_ADDRESS),
        "BOX_CONFIRM": ("box", texts.BOX_CONFIRM),
        "BOX_PAYMENT": ("box", texts.BOX_PAYMENT),
        "BOX_THANKS": ("box", texts.BOX_THANKS),
        "BOX_CONFIRMED": ("box", texts.BOX_CONFIRMED),
        "BOX_LATER": ("box", texts.BOX_LATER),
        # Заказы
        "WELCOME": ("order", texts.WELCOME),
        "ABOUT": ("order", texts.ABOUT),
        "ORDER_START": ("order", texts.ORDER_START),
        "ORDER_EMAIL": ("order", texts.ORDER_EMAIL),
        "ORDER_CONFIRM": ("order", texts.ORDER_CONFIRM),
        "ORDER_PAYMENT": ("order", texts.ORDER_PAYMENT),
        "ORDER_THANKS": ("order", texts.ORDER_THANKS),
        "ORDER_CONFIRMED": ("order", texts.ORDER_CONFIRMED),
        # Система
        "HELP": ("system", texts.HELP),
    }

    for key, (category, text) in ui_texts.items():
        props = {
            "Key": make_title(key),
            "Category": make_select(category),
            "Text": make_rich_text(text),
        }
        await create_page(client, UI_TEXTS_DB_ID, props)
        print(f"  {key}")
        await asyncio.sleep(0.35)

    print("UI тексты мигрированы!")


async def main():
    # Проверка настроек
    if not NOTION_TOKEN:
        print("Ошибка: NOTION_TOKEN не установлен")
        print("Установи переменную окружения или отредактируй скрипт")
        sys.exit(1)

    if not CONTENT_DB_ID:
        print("Ошибка: NOTION_CONTENT_DB не установлен")
        sys.exit(1)

    if not UI_TEXTS_DB_ID:
        print("Ошибка: NOTION_UI_TEXTS_DB не установлен")
        sys.exit(1)

    print("Миграция контента в Notion")
    print(f"Content DB: {CONTENT_DB_ID}")
    print(f"UI Texts DB: {UI_TEXTS_DB_ID}")

    async with httpx.AsyncClient(
        base_url="https://api.notion.com/v1",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    ) as client:
        await migrate_content(client)
        await migrate_ui_texts(client)

    print("\n=== Миграция завершена! ===")
    print("\nТеперь добавь в .env:")
    print(f"NOTION_TOKEN={NOTION_TOKEN}")
    print(f"NOTION_CONTENT_DB={CONTENT_DB_ID}")
    print(f"NOTION_UI_TEXTS_DB={UI_TEXTS_DB_ID}")
    print("\nИ запусти /sync в боте для синхронизации")


if __name__ == "__main__":
    asyncio.run(main())
