import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select, func
from datetime import datetime, timezone

import texts
from config import Config
from database import get_session, Order, OrderStatus, User, BoxOrder, BoxOrderStatus
from notion_sync import NotionSyncService
from content import ContentManager

router = Router()
logger = logging.getLogger(__name__)


def admin_only(config: Config):
    """Фильтр для админских команд."""
    async def check(message: Message) -> bool:
        return message.from_user.id == config.admin_id
    return check


@router.message(Command("orders"))
async def cmd_orders(message: Message, config: Config):
    if message.from_user.id != config.admin_id:
        return
    
    async with get_session() as session:
        result = await session.execute(
            select(Order).order_by(Order.created_at.desc()).limit(10)
        )
        orders = result.scalars().all()
    
    if not orders:
        await message.answer("Заказов пока нет.")
        return
    
    text = "Последние заказы:\n\n"
    for order in orders:
        status_emoji = {
            OrderStatus.PENDING: "⏳",
            OrderStatus.PAID: "💰",
            OrderStatus.CONFIRMED: "✅",
            OrderStatus.CANCELLED: "❌"
        }
        text += f"{status_emoji.get(order.status, '?')} #{order.id} | {order.name} | {order.phone} | {order.status.value}\n"
    
    await message.answer(text)


@router.message(Command("stats"))
async def cmd_stats(message: Message, config: Config):
    """Статистика заказов и пользователей."""
    if message.from_user.id != config.admin_id:
        return

    async with get_session() as session:
        # Пользователи - эффективный COUNT
        users_count_result = await session.execute(
            select(func.count()).select_from(User)
        )
        users_count = users_count_result.scalar() or 0

        # Общее количество заказов
        total_result = await session.execute(
            select(func.count()).select_from(Order)
        )
        total_orders = total_result.scalar() or 0

        # Заказы по статусам - эффективные запросы
        pending_result = await session.execute(
            select(func.count()).select_from(Order).where(Order.status == OrderStatus.PENDING)
        )
        pending = pending_result.scalar() or 0

        paid_result = await session.execute(
            select(func.count()).select_from(Order).where(Order.status == OrderStatus.PAID)
        )
        paid = paid_result.scalar() or 0

        confirmed_result = await session.execute(
            select(func.count()).select_from(Order).where(Order.status == OrderStatus.CONFIRMED)
        )
        confirmed = confirmed_result.scalar() or 0

        # Выручка Order - SUM с WHERE
        revenue_result = await session.execute(
            select(func.coalesce(func.sum(Order.amount), 0))
            .where(Order.status == OrderStatus.CONFIRMED)
        )
        total_revenue = revenue_result.scalar() or 0

        # === BoxOrder статистика ===
        box_total_result = await session.execute(
            select(func.count()).select_from(BoxOrder)
        )
        box_total = box_total_result.scalar() or 0

        box_pending_result = await session.execute(
            select(func.count()).select_from(BoxOrder).where(BoxOrder.status == BoxOrderStatus.PENDING)
        )
        box_pending = box_pending_result.scalar() or 0

        box_paid_result = await session.execute(
            select(func.count()).select_from(BoxOrder).where(BoxOrder.status == BoxOrderStatus.PAID)
        )
        box_paid = box_paid_result.scalar() or 0

        box_confirmed_result = await session.execute(
            select(func.count()).select_from(BoxOrder).where(BoxOrder.status == BoxOrderStatus.CONFIRMED)
        )
        box_confirmed = box_confirmed_result.scalar() or 0

        # Выручка BoxOrder
        box_revenue_result = await session.execute(
            select(func.coalesce(func.sum(BoxOrder.amount), 0))
            .where(BoxOrder.status.in_([BoxOrderStatus.CONFIRMED, BoxOrderStatus.SHIPPED, BoxOrderStatus.DELIVERED]))
        )
        box_revenue = box_revenue_result.scalar() or 0

    text = f"""Статистика

Пользователей: {users_count}

--- Заказы ---
Всего: {total_orders}
⏳ Ожидают оплаты: {pending}
💰 Оплачено (не подтв.): {paid}
✅ Подтверждено: {confirmed}
Выручка: {total_revenue} €

--- Предзаказы набора ---
Всего: {box_total}
⏳ Ожидают оплаты: {box_pending}
💰 Оплачено (не подтв.): {box_paid}
✅ Подтверждено: {box_confirmed}
Выручка: {box_revenue} €"""

    await message.answer(text)


@router.callback_query(F.data.startswith("confirm_"))
async def admin_confirm_order(callback: CallbackQuery, bot: Bot, config: Config):
    """Подтверждение заказа админом."""
    # Проверка что это админ
    if callback.from_user.id != config.admin_id:
        await callback.answer("Нет доступа")
        return

    # Строгий парсинг order_id: ожидаем ровно "confirm_123"
    parts = callback.data.split("_")
    if len(parts) != 2:
        logger.warning(f"Invalid callback format: {callback.data[:50]}")
        await callback.answer("Ошибка данных")
        return
    try:
        order_id = int(parts[1])
    except ValueError:
        logger.warning(f"Invalid order_id in callback: {callback.data[:50]}")
        await callback.answer("Ошибка данных")
        return

    async with get_session() as session:
        # Row-level lock для предотвращения race condition
        result = await session.execute(
            select(Order).where(Order.id == order_id).with_for_update()
        )
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer("Заказ не найден")
            return

        # Проверка что заказ ещё не обработан
        if order.status not in (OrderStatus.PENDING, OrderStatus.PAID):
            await callback.answer("Заказ уже обработан")
            return

        order.status = OrderStatus.CONFIRMED
        order.confirmed_at = datetime.now(timezone.utc)
        await session.commit()

        # Уведомляем пользователя (с обработкой ошибок)
        try:
            await bot.send_message(
                order.telegram_id,
                texts.ORDER_CONFIRMED
            )
        except TelegramAPIError as e:
            logger.warning(f"Failed to notify user {order.telegram_id}: {e}")

        try:
            await callback.message.edit_text(
                f"✅ Заказ #{order_id} подтверждён."
            )
        except TelegramAPIError:
            pass  # Сообщение уже изменено

    await callback.answer("Подтверждено")


@router.callback_query(F.data.startswith("reject_"))
async def admin_reject_order(callback: CallbackQuery, bot: Bot, config: Config):
    """Отклонение заказа админом."""
    # Проверка что это админ
    if callback.from_user.id != config.admin_id:
        await callback.answer("Нет доступа")
        return

    # Строгий парсинг order_id: ожидаем ровно "reject_123"
    parts = callback.data.split("_")
    if len(parts) != 2:
        logger.warning(f"Invalid callback format: {callback.data[:50]}")
        await callback.answer("Ошибка данных")
        return
    try:
        order_id = int(parts[1])
    except ValueError:
        logger.warning(f"Invalid order_id in callback: {callback.data[:50]}")
        await callback.answer("Ошибка данных")
        return

    async with get_session() as session:
        # Row-level lock для предотвращения race condition
        result = await session.execute(
            select(Order).where(Order.id == order_id).with_for_update()
        )
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer("Заказ не найден")
            return

        # Проверка что заказ ещё не обработан
        if order.status == OrderStatus.CANCELLED:
            await callback.answer("Заказ уже отклонён")
            return

        if order.status == OrderStatus.CONFIRMED:
            await callback.answer("Заказ уже подтверждён")
            return

        order.status = OrderStatus.CANCELLED
        await session.commit()

        # Уведомляем пользователя (с обработкой ошибок)
        try:
            await bot.send_message(
                order.telegram_id,
                "К сожалению, мы не смогли подтвердить оплату. Напиши нам, если есть вопросы."
            )
        except TelegramAPIError as e:
            logger.warning(f"Failed to notify user {order.telegram_id}: {e}")

        try:
            await callback.message.edit_text(f"❌ Заказ #{order_id} отклонён.")
        except TelegramAPIError:
            pass

    await callback.answer("Отклонено")


# ===== АДМИНКА ДЛЯ ПРЕДЗАКАЗОВ НАБОРА =====

@router.callback_query(F.data.startswith("box_confirm_"))
async def admin_confirm_box_order(callback: CallbackQuery, bot: Bot, config: Config):
    """Подтверждение предзаказа набора админом."""
    # Проверка что это админ
    if callback.from_user.id != config.admin_id:
        await callback.answer("Нет доступа")
        return

    # Строгий парсинг order_id: ожидаем ровно "box_confirm_123"
    parts = callback.data.split("_")
    if len(parts) != 3:
        logger.warning(f"Invalid callback format: {callback.data[:50]}")
        await callback.answer("Ошибка данных")
        return
    try:
        order_id = int(parts[2])
    except ValueError:
        logger.warning(f"Invalid order_id in callback: {callback.data[:50]}")
        await callback.answer("Ошибка данных")
        return

    async with get_session() as session:
        # Row-level lock для предотвращения race condition
        result = await session.execute(
            select(BoxOrder).where(BoxOrder.id == order_id).with_for_update()
        )
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer("Заказ не найден")
            return

        # Проверка что заказ ещё не обработан
        if order.status not in (BoxOrderStatus.PENDING, BoxOrderStatus.PAID):
            await callback.answer("Заказ уже обработан")
            return

        order.status = BoxOrderStatus.CONFIRMED
        await session.commit()

        # Уведомляем пользователя
        try:
            # Безопасный парсинг box_month (формат YYYY-MM)
            month_num = 0
            if order.box_month and len(order.box_month) >= 7:
                try:
                    month_num = int(order.box_month[5:7])
                except ValueError:
                    pass
            month_display = texts.MONTHS_GENITIVE.get(month_num, order.box_month or "—")
            await bot.send_message(
                order.telegram_id,
                texts.BOX_CONFIRMED.format(month=month_display)
            )
        except TelegramAPIError as e:
            logger.warning(f"Failed to notify user {order.telegram_id}: {e}")

        try:
            await callback.message.edit_text(
                f"✅ Предзаказ набора #{order_id} подтверждён."
            )
        except TelegramAPIError:
            pass

    await callback.answer("Подтверждено")


@router.callback_query(F.data.startswith("box_reject_"))
async def admin_reject_box_order(callback: CallbackQuery, bot: Bot, config: Config):
    """Отклонение предзаказа набора админом."""
    # Проверка что это админ
    if callback.from_user.id != config.admin_id:
        await callback.answer("Нет доступа")
        return

    # Строгий парсинг order_id: ожидаем ровно "box_reject_123"
    parts = callback.data.split("_")
    if len(parts) != 3:
        logger.warning(f"Invalid callback format: {callback.data[:50]}")
        await callback.answer("Ошибка данных")
        return
    try:
        order_id = int(parts[2])
    except ValueError:
        logger.warning(f"Invalid order_id in callback: {callback.data[:50]}")
        await callback.answer("Ошибка данных")
        return

    async with get_session() as session:
        # Row-level lock для предотвращения race condition
        result = await session.execute(
            select(BoxOrder).where(BoxOrder.id == order_id).with_for_update()
        )
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer("Заказ не найден")
            return

        # Проверка что заказ ещё не обработан
        if order.status == BoxOrderStatus.CANCELLED:
            await callback.answer("Заказ уже отклонён")
            return

        if order.status in (BoxOrderStatus.CONFIRMED, BoxOrderStatus.SHIPPED, BoxOrderStatus.DELIVERED):
            await callback.answer("Заказ уже обработан")
            return

        order.status = BoxOrderStatus.CANCELLED
        await session.commit()

        # Уведомляем пользователя
        try:
            await bot.send_message(
                order.telegram_id,
                "К сожалению, мы не смогли подтвердить оплату набора. Напиши нам, если есть вопросы."
            )
        except TelegramAPIError as e:
            logger.warning(f"Failed to notify user {order.telegram_id}: {e}")

        try:
            await callback.message.edit_text(f"❌ Предзаказ набора #{order_id} отклонён.")
        except TelegramAPIError:
            pass

    await callback.answer("Отклонено")


# ===== СИНХРОНИЗАЦИЯ С NOTION =====

@router.message(Command("sync"))
async def cmd_sync(message: Message, config: Config):
    """Синхронизация контента с Notion."""
    if message.from_user.id != config.admin_id:
        return

    # Проверка конфигурации
    if not config.notion_token:
        await message.answer("NOTION_TOKEN не настроен.\n\nДобавь в .env:\nNOTION_TOKEN=secret_xxx")
        return

    status_msg = await message.answer("Синхронизация...")

    try:
        # Синхронизируем
        sync_service = NotionSyncService(config)
        result = await sync_service.sync_all()

        # Перезагружаем in-memory кэш
        content_manager = ContentManager.get_instance()
        await content_manager.reload()

        # Валидация ключей UI
        missing = content_manager.validate_ui_keys()

        # Формируем отчет
        text = f"""Синхронизация завершена

Контент: {result['content']} записей
UI тексты: {result['ui_texts']} записей"""

        if missing:
            text += f"\n\n⚠️ Отсутствуют ключи:\n{', '.join(missing[:10])}"
            if len(missing) > 10:
                text += f"\n...и ещё {len(missing) - 10}"

        if result["errors"]:
            text += f"\n\nОшибки:\n" + "\n".join(result["errors"])

        await status_msg.edit_text(text)

    except Exception as e:
        logger.exception("Sync failed")
        await status_msg.edit_text(f"Ошибка синхронизации:\n{e}")


