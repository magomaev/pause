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
        text += f"{status_emoji.get(order.status, '?')} #{order.id} | {order.name} | {order.email} | {order.status.value}\n"
    
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

        # Выручка - SUM с WHERE
        revenue_result = await session.execute(
            select(func.coalesce(func.sum(Order.amount), 0))
            .where(Order.status == OrderStatus.CONFIRMED)
        )
        total_revenue = revenue_result.scalar() or 0

    text = f"""Статистика

Пользователей: {users_count}
Заказов всего: {total_orders}

⏳ Ожидают оплаты: {pending}
💰 Оплачено (не подтв.): {paid}
✅ Подтверждено: {confirmed}

Выручка: {total_revenue} €"""

    await message.answer(text)


@router.callback_query(F.data.startswith("confirm_"))
async def admin_confirm_order(callback: CallbackQuery, bot: Bot, config: Config):
    """Подтверждение заказа админом."""
    # Проверка что это админ
    if callback.from_user.id != config.admin_id:
        await callback.answer("Нет доступа")
        return

    # Безопасный парсинг order_id
    try:
        order_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        logger.error(f"Invalid callback data: {callback.data}")
        await callback.answer("Ошибка данных")
        return

    async with get_session() as session:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer("Заказ не найден")
            return

        # Проверка что заказ ещё не обработан
        if order.status not in (OrderStatus.PENDING, OrderStatus.PAID):
            await callback.answer(f"Заказ уже {order.status.value}")
            return

        order.status = OrderStatus.CONFIRMED
        order.confirmed_at = datetime.now(timezone.utc)
        await session.commit()

        # Уведомляем пользователя (с обработкой ошибок)
        try:
            await bot.send_message(
                order.telegram_id,
                texts.ORDER_CONFIRMED.format(email=order.email or "указанную почту")
            )
        except TelegramAPIError as e:
            logger.warning(f"Failed to notify user {order.telegram_id}: {e}")

        try:
            await callback.message.edit_text(
                f"✅ Заказ #{order_id} подтверждён.\nДоступ отправлен на {order.email}."
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

    # Безопасный парсинг order_id
    try:
        order_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        logger.error(f"Invalid callback data: {callback.data}")
        await callback.answer("Ошибка данных")
        return

    async with get_session() as session:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
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

    # Безопасный парсинг order_id
    try:
        order_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        logger.error(f"Invalid callback data: {callback.data}")
        await callback.answer("Ошибка данных")
        return

    async with get_session() as session:
        result = await session.execute(
            select(BoxOrder).where(BoxOrder.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer("Заказ не найден")
            return

        # Проверка что заказ ещё не обработан
        if order.status not in (BoxOrderStatus.PENDING, BoxOrderStatus.PAID):
            await callback.answer(f"Заказ уже {order.status.value}")
            return

        order.status = BoxOrderStatus.CONFIRMED
        await session.commit()

        # Уведомляем пользователя
        try:
            month_display = texts.MONTHS_GENITIVE.get(
                int(order.box_month.split("-")[1]), order.box_month
            )
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

    # Безопасный парсинг order_id
    try:
        order_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        logger.error(f"Invalid callback data: {callback.data}")
        await callback.answer("Ошибка данных")
        return

    async with get_session() as session:
        result = await session.execute(
            select(BoxOrder).where(BoxOrder.id == order_id)
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
