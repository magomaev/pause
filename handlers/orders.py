import re
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from datetime import datetime, timezone

import texts
import keyboards
from config import Config
from database import get_session, Order, OrderStatus

router = Router()
logger = logging.getLogger(__name__)

# Regex для валидации телефона (международный формат)
PHONE_REGEX = re.compile(r'^\+?[\d\s\-\(\)]{7,20}$')

# Ограничения
MAX_NAME_LENGTH = 100
MIN_NAME_LENGTH = 2
MIN_ADDRESS_LENGTH = 10


class OrderForm(StatesGroup):
    name = State()
    phone = State()
    address = State()
    confirm = State()


def validate_name(name: str) -> tuple[bool, str]:
    """Валидация имени. Возвращает (valid, error_message)."""
    if not name or not name.strip():
        return False, "Имя не может быть пустым. Попробуй ещё раз."

    name = name.strip()
    if len(name) < MIN_NAME_LENGTH:
        return False, f"Имя слишком короткое. Минимум {MIN_NAME_LENGTH} символа."

    if len(name) > MAX_NAME_LENGTH:
        return False, f"Имя слишком длинное. Максимум {MAX_NAME_LENGTH} символов."

    return True, ""


def validate_phone(phone: str) -> tuple[bool, str]:
    """Валидация телефона. Возвращает (valid, error_message)."""
    if not phone or not phone.strip():
        return False, "Телефон не может быть пустым. Попробуй ещё раз."

    phone = phone.strip()
    if not PHONE_REGEX.match(phone):
        return False, "Похоже, это не телефон. Укажи номер в международном формате, например: +7 999 123 45 67"

    return True, ""


def validate_address(address: str) -> tuple[bool, str]:
    """Валидация адреса. Возвращает (valid, error_message)."""
    if not address or not address.strip():
        return False, "Адрес не может быть пустым. Попробуй ещё раз."

    address = address.strip()
    if len(address) < MIN_ADDRESS_LENGTH:
        return False, "Адрес слишком короткий. Укажи полный адрес: страна, город, улица, дом, квартира, индекс."

    return True, ""


@router.callback_query(F.data == "order")
async def start_order(callback: CallbackQuery, state: FSMContext):
    """Начало оформления заказа."""
    await state.clear()  # Очищаем предыдущее состояние
    await state.set_state(OrderForm.name)

    try:
        await callback.message.edit_text(texts.ORDER_START)
    except TelegramAPIError:
        pass

    # Скрываем reply keyboard на время ввода данных
    await callback.message.answer(texts.ORDER_START, reply_markup=keyboards.remove_reply_keyboard())

    await callback.answer()


@router.message(OrderForm.name)
async def process_name(message: Message, state: FSMContext):
    """Обработка имени пользователя."""
    valid, error = validate_name(message.text)
    if not valid:
        await message.answer(error)
        return

    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(OrderForm.phone)
    await message.answer(texts.ORDER_PHONE)


@router.message(OrderForm.phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка телефона пользователя."""
    valid, error = validate_phone(message.text)
    if not valid:
        await message.answer(error)
        return

    phone = message.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.address)
    await message.answer(texts.ORDER_ADDRESS)


@router.message(OrderForm.address)
async def process_address(message: Message, state: FSMContext):
    """Обработка адреса пользователя."""
    valid, error = validate_address(message.text)
    if not valid:
        await message.answer(error)
        return

    address = message.text.strip()
    await state.update_data(address=address)
    data = await state.get_data()

    await state.set_state(OrderForm.confirm)
    await message.answer(
        texts.ORDER_CONFIRM.format(name=data["name"], phone=data["phone"], address=address),
        reply_markup=keyboards.confirm_order()
    )


@router.callback_query(OrderForm.confirm, F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext, config: Config, bot: Bot):
    """Подтверждение и создание заказа."""
    # Получаем данные ДО очистки state (защита от double-click)
    data = await state.get_data()

    # Проверяем что данные есть
    if not data or "name" not in data or "phone" not in data or "address" not in data:
        await callback.answer("Сессия истекла. Начни заново с /start")
        await state.clear()
        return

    # Сразу очищаем state чтобы повторный клик не создал второй заказ
    await state.clear()

    # Сохраняем заказ в базу
    async with get_session() as session:
        order = Order(
            telegram_id=callback.from_user.id,
            name=data["name"],
            phone=data["phone"],
            address=data["address"],
            amount=config.product_price,
            currency=config.product_currency,
            status=OrderStatus.PENDING
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)  # Получаем ID после commit
        order_id = order.id

    # Отправляем ссылку на оплату
    try:
        await callback.message.edit_text(
            texts.ORDER_PAYMENT,
            reply_markup=keyboards.payment_menu(config.payment_link)
        )
    except TelegramAPIError:
        await callback.message.answer(
            texts.ORDER_PAYMENT,
            reply_markup=keyboards.payment_menu(config.payment_link)
        )

    # Уведомляем админа (с обработкой ошибок)
    admin_text = f"""Новый заказ #{order_id}

Имя: {data["name"]}
Телефон: {data["phone"]}
Адрес: {data["address"]}
Сумма: {config.product_price} {config.product_currency}
Telegram: @{callback.from_user.username or "—"}"""

    try:
        await bot.send_message(
            config.admin_id,
            admin_text,
            reply_markup=keyboards.admin_order_menu(order_id)
        )
    except TelegramAPIError as e:
        logger.error(f"Failed to notify admin about order #{order_id}: {e}")

    await callback.answer()


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """Отмена заказа."""
    await state.clear()

    try:
        await callback.message.edit_text(texts.WELCOME, reply_markup=keyboards.main_menu())
    except TelegramAPIError:
        pass

    # Возвращаем reply keyboard
    await callback.message.answer(texts.WELCOME, reply_markup=keyboards.main_reply_keyboard())

    await callback.answer()


@router.callback_query(F.data == "i_paid")
async def user_paid(callback: CallbackQuery, bot: Bot, config: Config):
    """Пользователь отметил оплату."""
    order_phone = "указанный номер"

    async with get_session() as session:
        result = await session.execute(
            select(Order)
            .where(Order.telegram_id == callback.from_user.id)
            .where(Order.status == OrderStatus.PENDING)
            .order_by(Order.created_at.desc())
        )
        order = result.scalar_one_or_none()

        if order:
            # Проверяем статус ещё раз (защита от race condition)
            if order.status != OrderStatus.PENDING:
                await callback.answer("Заказ уже обработан")
                return

            order.status = OrderStatus.PAID
            order.paid_at = datetime.now(timezone.utc)
            await session.commit()
            order_phone = order.phone or order_phone
            order_id = order.id

            # Уведомляем админа (с обработкой ошибок)
            try:
                await bot.send_message(
                    config.admin_id,
                    f"💰 Пользователь отметил оплату заказа #{order_id}\n\nПроверь и подтверди.",
                    reply_markup=keyboards.admin_order_menu(order_id)
                )
            except TelegramAPIError as e:
                logger.error(f"Failed to notify admin about payment #{order_id}: {e}")
        else:
            await callback.answer("Заказ не найден")

    # Завершённое действие — отправляем новым сообщением, возвращаем меню
    await callback.message.answer(
        texts.ORDER_THANKS.format(phone=order_phone),
        reply_markup=keyboards.main_reply_keyboard()
    )

    await callback.answer()
