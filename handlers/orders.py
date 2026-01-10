from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from datetime import datetime

import texts
import keyboards
from config import Config
from database import get_session, Order, OrderStatus

router = Router()


class OrderForm(StatesGroup):
    name = State()
    email = State()
    confirm = State()


@router.callback_query(F.data == "order")
async def start_order(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderForm.name)
    await callback.message.edit_text(texts.ORDER_START)
    await callback.answer()


@router.message(OrderForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.email)
    await message.answer(texts.ORDER_EMAIL)


@router.message(OrderForm.email)
async def process_email(message: Message, state: FSMContext):
    email = message.text
    
    # Простая валидация email
    if "@" not in email or "." not in email:
        await message.answer("Похоже, это не email. Попробуй ещё раз.")
        return
    
    await state.update_data(email=email)
    data = await state.get_data()
    
    await state.set_state(OrderForm.confirm)
    await message.answer(
        texts.ORDER_CONFIRM.format(name=data["name"], email=data["email"]),
        reply_markup=keyboards.confirm_order()
    )


@router.callback_query(F.data == "confirm_order", OrderForm.confirm)
async def confirm_order(callback: CallbackQuery, state: FSMContext, config: Config, bot: Bot):
    data = await state.get_data()
    
    # Сохраняем заказ в базу
    async with get_session() as session:
        order = Order(
            telegram_id=callback.from_user.id,
            name=data["name"],
            email=data["email"],
            amount=config.product_price,
            currency=config.product_currency,
            status=OrderStatus.PENDING
        )
        session.add(order)
        await session.commit()
        order_id = order.id
    
    await state.clear()
    
    # Отправляем ссылку на оплату
    await callback.message.edit_text(
        texts.ORDER_PAYMENT,
        reply_markup=keyboards.payment_menu(config.payment_link)
    )
    
    # Уведомляем админа
    admin_text = f"""Новый заказ #{order_id}

Имя: {data["name"]}
Email: {data["email"]}
Сумма: {config.product_price} {config.product_currency}
Telegram: @{callback.from_user.username or "—"}"""
    
    await bot.send_message(
        config.admin_id,
        admin_text,
        reply_markup=keyboards.admin_order_menu(order_id)
    )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(texts.WELCOME, reply_markup=keyboards.main_menu())
    await callback.answer()


@router.callback_query(F.data == "i_paid")
async def user_paid(callback: CallbackQuery, bot: Bot, config: Config):
    # Обновляем статус заказа
    async with get_session() as session:
        result = await session.execute(
            select(Order)
            .where(Order.telegram_id == callback.from_user.id)
            .where(Order.status == OrderStatus.PENDING)
            .order_by(Order.created_at.desc())
        )
        order = result.scalar_one_or_none()
        
        if order:
            order.status = OrderStatus.PAID
            order.paid_at = datetime.utcnow()
            await session.commit()
            
            # Уведомляем админа
            await bot.send_message(
                config.admin_id,
                f"💰 Пользователь отметил оплату заказа #{order.id}\n\nПроверь и подтверди.",
                reply_markup=keyboards.admin_order_menu(order.id)
            )
    
    await callback.message.edit_text(
        texts.ORDER_THANKS.format(email=order.email if order else "указанную почту")
    )
    await callback.answer()
