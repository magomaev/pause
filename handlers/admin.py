from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select
from datetime import datetime

import texts
from config import Config
from database import get_session, Order, OrderStatus, User

router = Router()


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
    if message.from_user.id != config.admin_id:
        return
    
    async with get_session() as session:
        # Пользователи
        users_result = await session.execute(select(User))
        users_count = len(users_result.scalars().all())
        
        # Заказы по статусам
        orders_result = await session.execute(select(Order))
        orders = orders_result.scalars().all()
        
        pending = sum(1 for o in orders if o.status == OrderStatus.PENDING)
        paid = sum(1 for o in orders if o.status == OrderStatus.PAID)
        confirmed = sum(1 for o in orders if o.status == OrderStatus.CONFIRMED)
        
        total_revenue = sum(o.amount for o in orders if o.status == OrderStatus.CONFIRMED)
    
    text = f"""Статистика

Пользователей: {users_count}
Заказов всего: {len(orders)}

⏳ Ожидают оплаты: {pending}
💰 Оплачено (не подтв.): {paid}
✅ Подтверждено: {confirmed}

Выручка: {total_revenue} €"""
    
    await message.answer(text)


@router.callback_query(F.data.startswith("confirm_"))
async def admin_confirm_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    
    async with get_session() as session:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if order:
            order.status = OrderStatus.CONFIRMED
            order.confirmed_at = datetime.utcnow()
            await session.commit()
            
            # Уведомляем пользователя
            await bot.send_message(
                order.telegram_id,
                texts.ORDER_CONFIRMED.format(email=order.email)
            )
            
            await callback.message.edit_text(
                f"✅ Заказ #{order_id} подтверждён.\nДоступ отправлен на {order.email}."
            )
    
    await callback.answer("Подтверждено")


@router.callback_query(F.data.startswith("reject_"))
async def admin_reject_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    
    async with get_session() as session:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if order:
            order.status = OrderStatus.CANCELLED
            await session.commit()
            
            # Уведомляем пользователя
            await bot.send_message(
                order.telegram_id,
                "К сожалению, мы не смогли подтвердить оплату. Напиши нам, если есть вопросы."
            )
            
            await callback.message.edit_text(f"❌ Заказ #{order_id} отклонён.")
    
    await callback.answer("Отклонено")
