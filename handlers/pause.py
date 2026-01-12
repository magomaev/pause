"""
Отправка пауз пользователю.
"""
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError

import texts
import keyboards

router = Router()


@router.message(Command("pause"))
async def cmd_pause(message: Message):
    """Команда /pause — отправить случайную паузу."""
    pause_text = random.choice(texts.PAUSE_TEXTS)
    await message.answer(pause_text, reply_markup=keyboards.pause_menu())


@router.callback_query(F.data == "pause_now")
async def callback_pause_now(callback: CallbackQuery):
    """Кнопка 'Пауза сейчас'."""
    pause_text = random.choice(texts.PAUSE_TEXTS)

    try:
        await callback.message.edit_text(
            pause_text,
            reply_markup=keyboards.pause_menu()
        )
    except TelegramAPIError:
        await callback.message.answer(
            pause_text,
            reply_markup=keyboards.pause_menu()
        )

    await callback.answer()
