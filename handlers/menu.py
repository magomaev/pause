"""
Обработчики главного меню (команды и Reply Keyboard).
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter, Command

import texts
import keyboards
from content import ContentManager

router = Router()


# ===== КОМАНДЫ (кнопка Menu) =====

@router.message(Command("breathe"))
async def cmd_breathe(message: Message):
    """Команда /breathe — ссылка на медитацию."""
    content = ContentManager.get_instance()
    breathe_url = await content.get_random_breathe()
    await message.answer(breathe_url)


@router.message(Command("movie"))
async def cmd_movie(message: Message):
    """Команда /movie — ссылка на фильм."""
    content = ContentManager.get_instance()
    movie_url = await content.get_random_movie()
    await message.answer(movie_url)


@router.message(Command("book"))
async def cmd_book(message: Message):
    """Команда /book — ссылка на книгу."""
    content = ContentManager.get_instance()
    book_url = await content.get_random_book()
    await message.answer(book_url)


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Команда /settings — настройка напоминаний."""
    await message.answer(
        texts.ONBOARDING_ASK_REMINDERS,
        reply_markup=keyboards.onboarding_reminders()
    )


# ===== REPLY KEYBOARD =====


@router.message(F.text == texts.BTN_MENU_PAUSE, StateFilter(None))
async def menu_pause(message: Message):
    """Кнопка 'Пауза' — случайный текст из коротких пауз."""
    content = ContentManager.get_instance()
    pause_text = await content.get_random_pause_short()
    await message.answer(pause_text, reply_markup=keyboards.main_reply_keyboard())


@router.message(F.text == texts.BTN_MENU_LONG_PAUSE, StateFilter(None))
async def menu_long_pause(message: Message):
    """Кнопка 'Длинная пауза' — случайный контент (стихи, музыка, кино, книги)."""
    content = ContentManager.get_instance()
    long_content = await content.get_random_long_content()
    await message.answer(long_content, reply_markup=keyboards.main_reply_keyboard())


@router.message(F.text == texts.BTN_MENU_NEW_BOX, StateFilter(None))
async def menu_new_box(message: Message):
    """Кнопка 'Новый набор' — переход к предзаказу."""
    from handlers.box import get_box_month
    _, month_display = get_box_month()
    await message.answer(
        texts.BOX_INTRO.format(month=month_display),
        reply_markup=keyboards.box_intro()
    )


@router.message(F.text == texts.BTN_MENU_REMINDERS, StateFilter(None))
async def menu_reminders(message: Message):
    """Кнопка 'Напоминания' — настройка напоминаний."""
    await message.answer(
        texts.ONBOARDING_ASK_REMINDERS,
        reply_markup=keyboards.onboarding_reminders()
    )
