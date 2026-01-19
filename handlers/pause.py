"""
Отправка пауз пользователю.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

import keyboards
from content import ContentManager

router = Router()


@router.message(Command("pause"))
async def cmd_pause(message: Message):
    """Команда /pause — отправить случайную паузу (длинную)."""
    content = ContentManager.get_instance()
    pause_text = await content.get_random_pause_long()
    await message.answer(pause_text, reply_markup=keyboards.pause_menu())


@router.callback_query(F.data == "pause_now")
async def callback_pause_now(callback: CallbackQuery):
    """Кнопка 'Пауза сейчас' — длинный контент для осознанного запроса."""
    content = ContentManager.get_instance()
    pause_text = await content.get_random_pause_long()

    # Паузы — это завершённые действия, отправляем новым сообщением
    await callback.message.answer(
        pause_text,
        reply_markup=keyboards.pause_menu()
    )

    await callback.answer()
