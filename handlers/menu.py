"""
Обработчики главного меню (команды и Reply Keyboard).
"""
import random
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter, Command

import texts
import keyboards

router = Router()


# ===== КОМАНДЫ (кнопка Menu) =====

@router.message(Command("pause"))
async def cmd_pause(message: Message):
    """Команда /pause — случайный текст из длинных пауз."""
    pause_text = random.choice(texts.PAUSE_LONG)
    await message.answer(pause_text)


@router.message(Command("breathe"))
async def cmd_breathe(message: Message):
    """Команда /breathe — ссылка на медитацию."""
    breathe_url = random.choice(texts.BREATHE_CONTENT)
    await message.answer(breathe_url)


@router.message(Command("movie"))
async def cmd_movie(message: Message):
    """Команда /movie — ссылка на фильм."""
    movie_url = random.choice(texts.MOVIES)
    await message.answer(movie_url)


@router.message(Command("book"))
async def cmd_book(message: Message):
    """Команда /book — ссылка на книгу."""
    book_url = random.choice(texts.BOOKS)
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
    """Кнопка 'Пауза' — случайный текст из длинных пауз."""
    pause_text = random.choice(texts.PAUSE_LONG)
    await message.answer(pause_text, reply_markup=keyboards.main_reply_keyboard())


@router.message(F.text == texts.BTN_MENU_BREATHE, StateFilter(None))
async def menu_breathe(message: Message):
    """Кнопка 'Подышать' — ссылка на медитацию."""
    breathe_url = random.choice(texts.BREATHE_CONTENT)
    await message.answer(breathe_url, reply_markup=keyboards.main_reply_keyboard())


@router.message(F.text == texts.BTN_MENU_MOVIE, StateFilter(None))
async def menu_movie(message: Message):
    """Кнопка 'Кино' — ссылка на фильм."""
    movie_url = random.choice(texts.MOVIES)
    await message.answer(movie_url, reply_markup=keyboards.main_reply_keyboard())


@router.message(F.text == texts.BTN_MENU_BOOK, StateFilter(None))
async def menu_book(message: Message):
    """Кнопка 'Книга' — ссылка на книгу."""
    book_url = random.choice(texts.BOOKS)
    await message.answer(book_url, reply_markup=keyboards.main_reply_keyboard())


@router.message(F.text == texts.BTN_MENU_NEW_BOX, StateFilter(None))
async def menu_new_box(message: Message):
    """Кнопка 'Новый набор' — переход к предзаказу."""
    from handlers.box import get_box_month
    _, month_display = get_box_month()
    await message.answer(
        texts.BOX_INTRO.format(month=month_display),
        reply_markup=keyboards.box_intro()
    )


@router.message(F.text == texts.BTN_MENU_SETTINGS, StateFilter(None))
async def menu_settings(message: Message):
    """Кнопка 'Настроить паузу' — настройка напоминаний."""
    await message.answer(
        texts.ONBOARDING_ASK_REMINDERS,
        reply_markup=keyboards.onboarding_reminders()
    )
