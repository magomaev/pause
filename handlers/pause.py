"""
Отправка пауз пользователю.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from content import ContentManager

router = Router()


@router.message(Command("pause"))
async def cmd_pause(message: Message, state: FSMContext):
    """Команда /pause — стихи + музыка с чередованием типа."""
    data = await state.get_data()
    last_type = data.get("last_pause_type")

    content = ContentManager.get_instance()
    pause_text, content_type = await content.get_random_pause_excluding(last_type)

    await state.update_data(last_pause_type=content_type)
    await message.answer(pause_text)


@router.callback_query(F.data == "pause_now")
async def callback_pause_now(callback: CallbackQuery, state: FSMContext):
    """Кнопка 'Пауза сейчас' — стихи + музыка с чередованием типа."""
    data = await state.get_data()
    last_type = data.get("last_pause_type")

    content = ContentManager.get_instance()
    pause_text, content_type = await content.get_random_pause_excluding(last_type)

    await state.update_data(last_pause_type=content_type)

    # Паузы — это завершённые действия, отправляем новым сообщением
    await callback.message.answer(pause_text)

    await callback.answer()
