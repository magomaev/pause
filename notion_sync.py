"""
Синхронизация контента с Notion.
"""
import logging
from typing import Any

import httpx
from sqlalchemy import delete

from config import Config
from database import get_session, ContentCache, UITextCache

logger = logging.getLogger(__name__)


class NotionSyncService:
    """Сервис синхронизации контента с Notion."""

    def __init__(self, config: Config):
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Получить или создать HTTP клиент."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.notion.com/v1",
                headers={
                    "Authorization": f"Bearer {self.config.notion_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Закрыть HTTP клиент."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def sync_all(self) -> dict[str, Any]:
        """
        Полная синхронизация всех данных.

        Returns:
            dict с ключами: content (int), ui_texts (int), errors (list[str])
        """
        result = {"content": 0, "ui_texts": 0, "errors": []}

        try:
            if self.config.notion_content_db:
                content_count = await self._sync_content()
                result["content"] = content_count
                logger.info(f"Synced {content_count} content items")
            else:
                result["errors"].append("NOTION_CONTENT_DB не настроен")
        except Exception as e:
            logger.exception("Content sync failed")
            result["errors"].append(f"Контент: {e}")

        try:
            if self.config.notion_ui_texts_db:
                ui_count = await self._sync_ui_texts()
                result["ui_texts"] = ui_count
                logger.info(f"Synced {ui_count} UI texts")
            else:
                result["errors"].append("NOTION_UI_TEXTS_DB не настроен")
        except Exception as e:
            logger.exception("UI texts sync failed")
            result["errors"].append(f"UI тексты: {e}")

        await self.close()
        return result

    async def _fetch_all_pages(
        self, database_id: str, filter_obj: dict | None = None
    ) -> list[dict]:
        """
        Получить все страницы из базы с пагинацией.

        Args:
            database_id: ID базы данных Notion
            filter_obj: Опциональный фильтр для запроса

        Returns:
            Список всех страниц
        """
        client = await self._get_client()
        pages = []
        start_cursor = None

        while True:
            body: dict[str, Any] = {"page_size": 100}
            if start_cursor:
                body["start_cursor"] = start_cursor
            if filter_obj:
                body["filter"] = filter_obj

            response = await client.post(
                f"/databases/{database_id}/query",
                json=body,
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Notion API error: {response.status_code} - {error_text}")
                raise Exception(f"Notion API error: {response.status_code}")

            data = response.json()
            pages.extend(data.get("results", []))

            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")

        return pages

    def _extract_rich_text(self, blocks: list) -> str:
        """
        Объединить все блоки Rich Text в строку.

        Args:
            blocks: Список блоков rich_text из Notion API

        Returns:
            Объединённый текст
        """
        if not blocks:
            return ""
        return "".join(block.get("plain_text", "") for block in blocks)

    def _extract_title(self, title_blocks: list) -> str:
        """Извлечь текст из Title property."""
        return self._extract_rich_text(title_blocks)

    def _extract_select(self, select_obj: dict | None) -> str | None:
        """Извлечь значение из Select property."""
        if not select_obj:
            return None
        return select_obj.get("name")

    def _extract_checkbox(self, checkbox_value: bool | None) -> bool:
        """Извлечь значение из Checkbox property."""
        return checkbox_value is True

    async def _sync_content(self) -> int:
        """
        Синхронизация базы контента.

        Returns:
            Количество синхронизированных записей
        """
        # Получаем только активные записи
        pages = await self._fetch_all_pages(
            self.config.notion_content_db,
            filter_obj={"property": "Active", "checkbox": {"equals": True}},
        )

        async with get_session() as session:
            # Очищаем старый кэш
            await session.execute(delete(ContentCache))

            count = 0
            for page in pages:
                try:
                    props = page.get("properties", {})

                    # Type (Select)
                    content_type = self._extract_select(props.get("Type", {}).get("select"))
                    if not content_type:
                        logger.warning(f"Page {page['id']} has no Type, skipping")
                        continue

                    # Content (Rich Text)
                    content = self._extract_rich_text(
                        props.get("Content", {}).get("rich_text", [])
                    )
                    if not content:
                        logger.warning(f"Page {page['id']} has no Content, skipping")
                        continue

                    cache_entry = ContentCache(
                        content_type=content_type,
                        content=content,
                        notion_page_id=page["id"],
                        is_active=True,
                    )
                    session.add(cache_entry)
                    count += 1

                except Exception as e:
                    logger.warning(f"Failed to parse content page {page.get('id')}: {e}")

            await session.commit()

        return count

    async def _sync_ui_texts(self) -> int:
        """
        Синхронизация базы UI текстов.

        Returns:
            Количество синхронизированных записей
        """
        pages = await self._fetch_all_pages(self.config.notion_ui_texts_db)

        async with get_session() as session:
            # Очищаем старый кэш
            await session.execute(delete(UITextCache))

            count = 0
            for page in pages:
                try:
                    props = page.get("properties", {})

                    # Key (Title)
                    key = self._extract_title(props.get("Key", {}).get("title", []))
                    if not key:
                        logger.warning(f"UI page {page['id']} has no Key, skipping")
                        continue

                    # Text (Rich Text)
                    text = self._extract_rich_text(
                        props.get("Text", {}).get("rich_text", [])
                    )

                    cache_entry = UITextCache(
                        key=key,
                        text=text,
                        notion_page_id=page["id"],
                    )
                    session.add(cache_entry)
                    count += 1

                except Exception as e:
                    logger.warning(f"Failed to parse UI page {page.get('id')}: {e}")

            await session.commit()

        return count
