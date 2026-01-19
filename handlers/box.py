"""
Предзаказ физического набора «Пауза».

Новый флоу:
1. "Откликается" → Заказ создаётся в БД (PENDING)
2. Имя из Telegram → подтвердить или изменить
3. Телефон для связи
4. Адрес доставки
5. Подтверждение данных
6. Ссылка на оплату
"""
import re
import logging
from datetime import datetime, timezone
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select

import texts
import keyboards
from config import Config
from database import get_session, BoxOrder, BoxOrderStatus

router = Router()
logger = logging.getLogger(__name__)

# Кнопки reply keyboard — если пользователь нажал одну из них, выходим из FSM
MENU_BUTTONS = {
    texts.BTN_MENU_PAUSE,
    texts.BTN_MENU_LONG_PAUSE,
    texts.BTN_MENU_NEW_BOX,
    texts.BTN_MENU_REMINDERS,
}

# Ограничения
MAX_NAME_LENGTH = 100
MIN_NAME_LENGTH = 2
MAX_ADDRESS_LENGTH = 500
MIN_ADDRESS_LENGTH = 20

# Regex для валидации телефона
PHONE_REGEX = re.compile(r'^\+?[0-9\s\-\(\)]{7,20}$')


class BoxOrderForm(StatesGroup):
    """FSM для предзаказа набора."""
    name = State()      # Подтверждение/изменение имени
    phone = State()     # Ввод телефона
    address = State()   # Ввод адреса
    confirm = State()   # Подтверждение данных


def get_box_month() -> tuple[str, str]:
    """
    Определить месяц набора.
    До 20 числа → 1 следующего месяца.
    После 20 → 1 числа через месяц.

    Returns:
        (month_key, month_display): ("2026-02", "февраля")
    """
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    if now.day <= 20:
        # Набор будет 1 числа следующего месяца
        target_month = month + 1
        target_year = year
        if target_month > 12:
            target_month = 1
            target_year += 1
    else:
        # Набор будет 1 числа через месяц
        target_month = month + 2
        target_year = year
        if target_month > 12:
            target_month -= 12
            target_year += 1

    month_key = f"{target_year}-{target_month:02d}"
    month_display = texts.MONTHS_GENITIVE.get(target_month, str(target_month))

    return month_key, month_display


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
        return False, "Укажи корректный номер телефона."

    return True, ""


def validate_address(address: str) -> tuple[bool, str]:
    """Валидация адреса. Возвращает (valid, error_message)."""
    if not address or not address.strip():
        return False, "Адрес не может быть пустым. Попробуй ещё раз."

    address = address.strip()
    if len(address) < MIN_ADDRESS_LENGTH:
        return False, "Адрес слишком короткий. Укажи полный адрес с индексом."

    if len(address) > MAX_ADDRESS_LENGTH:
        return False, f"Адрес слишком длинный. Максимум {MAX_ADDRESS_LENGTH} символов."

    return True, ""


# ===== НАЧАЛО ПРЕДЗАКАЗА =====

@router.message(Command("box"))
async def cmd_box(message: Message, state: FSMContext):
    """Команда /box — начало предзаказа набора."""
    await state.clear()

    _, month_display = get_box_month()

    await message.answer(
        texts.BOX_INTRO.format(month=month_display),
        reply_markup=keyboards.box_intro()
    )


@router.callback_query(F.data == "get_box")
async def callback_get_box(callback: CallbackQuery, state: FSMContext):
    """Кнопка 'Получить набор'."""
    await state.clear()

    _, month_display = get_box_month()

    try:
        await callback.message.edit_text(
            texts.BOX_INTRO.format(month=month_display),
            reply_markup=keyboards.box_intro()
        )
    except TelegramAPIError:
        await callback.message.answer(
            texts.BOX_INTRO.format(month=month_display),
            reply_markup=keyboards.box_intro()
        )

    await callback.answer()


# ===== ОТКЛИКАЕТСЯ → СОЗДАНИЕ ЗАКАЗА + ЗАПРОС ИМЕНИ =====

@router.callback_query(F.data == "box_start")
async def box_start(callback: CallbackQuery, state: FSMContext, config: Config):
    """
    Пользователю откликается — создаём заказ в БД сразу.
    Показываем имя из Telegram для подтверждения.
    """
    month_key, month_display = get_box_month()

    # Создаём заказ в БД сразу (без phone/address — заполним позже)
    async with get_session() as session:
        order = BoxOrder(
            telegram_id=callback.from_user.id,
            box_month=month_key,
            amount=config.product_price,
            currency=config.product_currency,
            status=BoxOrderStatus.PENDING
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        order_id = order.id

    # Сохраняем order_id в FSM state
    telegram_name = callback.from_user.first_name or "Друг"
    await state.update_data(order_id=order_id, name=telegram_name)
    await state.set_state(BoxOrderForm.name)

    try:
        await callback.message.edit_text(
            texts.BOX_ASK_NAME.format(name=telegram_name),
            reply_markup=keyboards.box_confirm_name()
        )
    except TelegramAPIError:
        pass

    # Скрываем reply keyboard на время ввода данных
    await callback.message.answer(
        texts.BOX_ASK_NAME.format(name=telegram_name),
        reply_markup=keyboards.remove_reply_keyboard()
    )

    await callback.answer()


# ===== ПОДТВЕРЖДЕНИЕ ИМЕНИ КНОПКОЙ =====

@router.callback_query(BoxOrderForm.name, F.data == "box_name_ok")
async def box_name_confirmed(callback: CallbackQuery, state: FSMContext):
    """Пользователь подтвердил имя из Telegram кнопкой."""
    await state.set_state(BoxOrderForm.phone)

    try:
        await callback.message.edit_text(texts.BOX_ASK_PHONE)
    except TelegramAPIError:
        await callback.message.answer(texts.BOX_ASK_PHONE)

    await callback.answer()


# ===== ВВОД СВОЕГО ИМЕНИ =====

@router.message(BoxOrderForm.name, ~F.text.in_(MENU_BUTTONS))
async def process_box_name(message: Message, state: FSMContext):
    """Обработка нового имени (если пользователь хочет изменить)."""
    valid, error = validate_name(message.text)
    if not valid:
        await message.answer(error)
        return

    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(BoxOrderForm.phone)
    await message.answer(texts.BOX_ASK_PHONE)


# ===== ВВОД ТЕЛЕФОНА =====

@router.message(BoxOrderForm.phone, ~F.text.in_(MENU_BUTTONS))
async def process_box_phone(message: Message, state: FSMContext):
    """Обработка телефона."""
    valid, error = validate_phone(message.text)
    if not valid:
        await message.answer(error)
        return

    phone = message.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(BoxOrderForm.address)
    await message.answer(texts.BOX_ASK_ADDRESS)


# ===== ВВОД АДРЕСА =====

@router.message(BoxOrderForm.address, ~F.text.in_(MENU_BUTTONS))
async def process_box_address(message: Message, state: FSMContext):
    """Обработка адреса."""
    valid, error = validate_address(message.text)
    if not valid:
        await message.answer(error)
        return

    address = message.text.strip()
    await state.update_data(address=address)

    data = await state.get_data()
    _, month_display = get_box_month()

    await state.set_state(BoxOrderForm.confirm)
    await message.answer(
        texts.BOX_CONFIRM.format(
            name=data["name"],
            phone=data["phone"],
            address=address,
            month=month_display
        ),
        reply_markup=keyboards.box_confirm()
    )


# ===== ПОДТВЕРЖДЕНИЕ ДАННЫХ =====

@router.callback_query(BoxOrderForm.confirm, F.data == "box_confirm")
async def confirm_box_order(callback: CallbackQuery, state: FSMContext, config: Config, bot: Bot):
    """Подтверждение данных — обновляем заказ в БД, показываем оплату."""
    data = await state.get_data()

    # Проверяем что данные есть
    if not data or "order_id" not in data or "name" not in data or "phone" not in data or "address" not in data:
        await callback.answer("Сессия истекла. Начни заново с /box")
        await state.clear()
        return

    order_id = data["order_id"]

    # Очищаем state
    await state.clear()

    _, month_display = get_box_month()

    # Обновляем заказ в БД
    async with get_session() as session:
        result = await session.execute(
            select(BoxOrder).where(BoxOrder.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer("Заказ не найден")
            return

        order.name = data["name"]
        order.phone = data["phone"]
        order.address = data["address"]
        await session.commit()

    # Отправляем ссылку на оплату
    try:
        await callback.message.edit_text(
            texts.BOX_PAYMENT,
            reply_markup=keyboards.box_payment(config.payment_link)
        )
    except TelegramAPIError:
        await callback.message.answer(
            texts.BOX_PAYMENT,
            reply_markup=keyboards.box_payment(config.payment_link)
        )

    # Уведомляем админа
    admin_text = f"""Новый предзаказ набора #{order_id}

Имя: {data["name"]}
Телефон: {data["phone"]}
Адрес: {data["address"]}
Набор: 1 {month_display}
Сумма: {config.product_price} {config.product_currency}
Telegram: @{callback.from_user.username or "—"}"""

    try:
        await bot.send_message(
            config.admin_id,
            admin_text,
            reply_markup=keyboards.admin_box_order_menu(order_id)
        )
    except TelegramAPIError as e:
        logger.error(f"Failed to notify admin about box order #{order_id}: {e}")

    await callback.answer()


# ===== ОТМЕНА / ПОЗЖЕ =====

@router.callback_query(F.data == "box_later")
async def box_later(callback: CallbackQuery, state: FSMContext):
    """Вернуться позже."""
    await state.clear()

    # Завершённое действие — отправляем новым сообщением, возвращаем меню
    await callback.message.answer(
        texts.BOX_LATER,
        reply_markup=keyboards.main_reply_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data == "box_cancel")
async def box_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена заказа набора."""
    await state.clear()

    _, month_display = get_box_month()

    try:
        await callback.message.edit_text(
            texts.BOX_INTRO.format(month=month_display),
            reply_markup=keyboards.box_intro()
        )
    except TelegramAPIError:
        await callback.message.answer(
            texts.BOX_INTRO.format(month=month_display),
            reply_markup=keyboards.box_intro()
        )

    await callback.answer()


# ===== ОПЛАТА =====

@router.callback_query(F.data == "box_paid")
async def box_user_paid(callback: CallbackQuery, bot: Bot, config: Config):
    """Пользователь отметил оплату набора."""
    _, month_display = get_box_month()

    async with get_session() as session:
        result = await session.execute(
            select(BoxOrder)
            .where(BoxOrder.telegram_id == callback.from_user.id)
            .where(BoxOrder.status == BoxOrderStatus.PENDING)
            .order_by(BoxOrder.created_at.desc())
        )
        order = result.scalar_one_or_none()

        if order:
            # Проверяем статус ещё раз (защита от race condition)
            if order.status != BoxOrderStatus.PENDING:
                await callback.answer("Заказ уже обработан")
                return

            order.status = BoxOrderStatus.PAID
            order.paid_at = datetime.now(timezone.utc)
            await session.commit()
            order_id = order.id

            # Уведомляем админа
            try:
                await bot.send_message(
                    config.admin_id,
                    f"💰 Пользователь отметил оплату предзаказа набора #{order_id}\n\nПроверь и подтверди.",
                    reply_markup=keyboards.admin_box_order_menu(order_id)
                )
            except TelegramAPIError as e:
                logger.error(f"Failed to notify admin about box payment #{order_id}: {e}")
        else:
            await callback.answer("Заказ не найден")

    # Завершённое действие — отправляем новым сообщением, возвращаем меню
    await callback.message.answer(
        texts.BOX_THANKS.format(month=month_display),
        reply_markup=keyboards.main_reply_keyboard()
    )

    await callback.answer()
