"""
Онбординг пользователя — настройка напоминаний.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select

import texts
import keyboards
from database import get_session, User, ReminderFrequency, ReminderTime

router = Router()
logger = logging.getLogger(__name__)


class OnboardingForm(StatesGroup):
    """FSM для онбординга."""
    reminder_choice = State()  # Да/Нет на напоминания
    frequency = State()        # Выбор частоты
    time = State()             # Выбор времени


async def get_or_create_user(telegram_id: int, username: str | None, first_name: str | None) -> tuple[User, bool]:
    """Получить или создать пользователя. Возвращает (user, onboarding_completed)."""
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # Сохраняем значение до закрытия сессии
        onboarding_completed = user.onboarding_completed
        return user, onboarding_completed


async def update_user_settings(
    telegram_id: int,
    onboarding_completed: bool = True,
    reminder_enabled: bool = False,
    reminder_frequency: ReminderFrequency | None = None,
    reminder_time: ReminderTime | None = None
):
    """Обновить настройки пользователя."""
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.onboarding_completed = onboarding_completed
            user.reminder_enabled = reminder_enabled
            user.reminder_frequency = reminder_frequency
            user.reminder_time = reminder_time
            await session.commit()


# ===== ЭКРАН 0: ПРИВЕТСТВИЕ =====

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start — начало онбординга."""
    # Очищаем предыдущее состояние FSM
    await state.clear()

    # Получаем или создаём пользователя
    user, onboarding_completed = await get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    # Если онбординг пройден — показываем reply keyboard
    if onboarding_completed:
        await message.answer(
            texts.WELCOME_BACK,
            reply_markup=keyboards.main_reply_keyboard()
        )
        return

    # Иначе — начинаем онбординг
    await message.answer(
        texts.ONBOARDING_WELCOME,
        reply_markup=keyboards.onboarding_welcome()
    )


# ===== ЭКРАН 1: НУЖНЫ ЛИ НАПОМИНАНИЯ =====

@router.callback_query(F.data == "setup_pause")
async def setup_pause(callback: CallbackQuery, state: FSMContext):
    """Настроить паузу — спрашиваем о напоминаниях."""
    await state.set_state(OnboardingForm.reminder_choice)

    try:
        await callback.message.edit_text(
            texts.ONBOARDING_ASK_REMINDERS,
            reply_markup=keyboards.onboarding_reminders()
        )
    except TelegramAPIError:
        await callback.message.answer(
            texts.ONBOARDING_ASK_REMINDERS,
            reply_markup=keyboards.onboarding_reminders()
        )

    await callback.answer()


# ===== ЭКРАН 2A: БЕЗ НАПОМИНАНИЙ =====

@router.callback_query(F.data == "reminders_no")
async def reminders_no(callback: CallbackQuery, state: FSMContext):
    """Пользователь не хочет напоминания."""
    await state.clear()

    # Сохраняем настройки
    await update_user_settings(
        telegram_id=callback.from_user.id,
        onboarding_completed=True,
        reminder_enabled=False
    )

    # Убираем кнопки с предыдущего сообщения
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramAPIError:
        pass

    # Завершённое действие — отправляем новым сообщением с reply keyboard
    await callback.message.answer(
        texts.ONBOARDING_NO_REMINDERS,
        reply_markup=keyboards.main_reply_keyboard()
    )

    await callback.answer()


# ===== ЭКРАН 2B: ВЫБОР ЧАСТОТЫ =====

@router.callback_query(F.data == "reminders_yes")
async def reminders_yes(callback: CallbackQuery, state: FSMContext):
    """Пользователь хочет напоминания — спрашиваем частоту."""
    await state.set_state(OnboardingForm.frequency)

    try:
        await callback.message.edit_text(
            texts.ONBOARDING_ASK_FREQUENCY,
            reply_markup=keyboards.onboarding_frequency()
        )
    except TelegramAPIError:
        await callback.message.answer(
            texts.ONBOARDING_ASK_FREQUENCY,
            reply_markup=keyboards.onboarding_frequency()
        )

    await callback.answer()


# ===== ЭКРАН 3B: ВЫБОР ВРЕМЕНИ =====

@router.callback_query(F.data.startswith("freq_"))
async def select_frequency(callback: CallbackQuery, state: FSMContext):
    """Выбор частоты напоминаний."""
    freq_map = {
        "freq_daily": ReminderFrequency.DAILY,
        "freq_3_per_week": ReminderFrequency.THREE_PER_WEEK,
        "freq_weekly": ReminderFrequency.WEEKLY,
    }

    frequency = freq_map.get(callback.data)
    if not frequency:
        await callback.answer("Неизвестная частота")
        return

    await state.update_data(frequency=frequency)
    await state.set_state(OnboardingForm.time)

    try:
        await callback.message.edit_text(
            texts.ONBOARDING_ASK_TIME,
            reply_markup=keyboards.onboarding_time()
        )
    except TelegramAPIError:
        await callback.message.answer(
            texts.ONBOARDING_ASK_TIME,
            reply_markup=keyboards.onboarding_time()
        )

    await callback.answer()


# ===== ЭКРАН 4B: ПОДТВЕРЖДЕНИЕ =====

@router.callback_query(F.data.startswith("time_"))
async def select_time(callback: CallbackQuery, state: FSMContext):
    """Выбор времени напоминаний — завершение онбординга."""
    time_map = {
        "time_morning": ReminderTime.MORNING,
        "time_afternoon": ReminderTime.AFTERNOON,
        "time_evening": ReminderTime.EVENING,
        "time_random": ReminderTime.RANDOM,
    }

    reminder_time = time_map.get(callback.data)
    if not reminder_time:
        await callback.answer("Неизвестное время")
        return

    # Получаем частоту из state
    data = await state.get_data()
    frequency = data.get("frequency")

    if not frequency:
        # Если state потерян, возвращаем к началу
        await state.clear()
        await callback.answer("Сессия истекла. Начни заново с /start")
        return

    await state.clear()

    # Сохраняем настройки
    await update_user_settings(
        telegram_id=callback.from_user.id,
        onboarding_completed=True,
        reminder_enabled=True,
        reminder_frequency=frequency,
        reminder_time=reminder_time
    )

    # Формируем текст подтверждения
    freq_text_map = {
        ReminderFrequency.DAILY: texts.FREQUENCY_DAILY,
        ReminderFrequency.THREE_PER_WEEK: texts.FREQUENCY_3_PER_WEEK,
        ReminderFrequency.WEEKLY: texts.FREQUENCY_WEEKLY,
    }
    time_text_map = {
        ReminderTime.MORNING: texts.TIME_MORNING,
        ReminderTime.AFTERNOON: texts.TIME_AFTERNOON,
        ReminderTime.EVENING: texts.TIME_EVENING,
        ReminderTime.RANDOM: texts.TIME_RANDOM,
    }

    confirm_text = texts.ONBOARDING_CONFIRM.format(
        frequency_text=freq_text_map.get(frequency, ""),
        time_text=time_text_map.get(reminder_time, "")
    )

    # Убираем кнопки с предыдущего сообщения
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramAPIError:
        pass

    # Завершённое действие — отправляем новым сообщением с reply keyboard
    await callback.message.answer(
        confirm_text,
        reply_markup=keyboards.main_reply_keyboard()
    )

    await callback.answer()


# ===== КОМАНДА /help =====

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help."""
    await message.answer(texts.HELP)
