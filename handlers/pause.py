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
    """Команда /pause — отправить случайную паузу (длинную)."""
    pause_text = random.choice(texts.PAUSE_LONG)
    await message.answer(pause_text, reply_markup=keyboards.pause_menu())


@router.callback_query(F.data == "pause_now")
async def callback_pause_now(callback: CallbackQuery):
    """Кнопка 'Пауза сейчас' — длинный контент для осознанного запроса."""
    pause_text = random.choice(texts.PAUSE_LONG)

    # Паузы — это завершённые действия, отправляем новым сообщением
    await callback.message.answer(
        pause_text,
        reply_markup=keyboards.pause_menu()
    )

    await callback.answer()
