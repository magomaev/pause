from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from sqlalchemy import select

import texts
import keyboards
from database import get_session, User

router = Router()


async def save_user(telegram_id: int, username: str | None, first_name: str | None):
    """Сохраняем пользователя в базу если его нет."""
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


@router.message(CommandStart())
async def cmd_start(message: Message):
    await save_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    await message.answer(texts.WELCOME, reply_markup=keyboards.main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(texts.HELP)


@router.message(Command("about"))
async def cmd_about(message: Message):
    await message.answer(texts.ABOUT, reply_markup=keyboards.about_menu())


@router.callback_query(F.data == "back")
async def callback_back(callback: CallbackQuery):
    await callback.message.edit_text(texts.WELCOME, reply_markup=keyboards.main_menu())
    await callback.answer()


@router.callback_query(F.data == "about")
async def callback_about(callback: CallbackQuery):
    await callback.message.edit_text(texts.ABOUT, reply_markup=keyboards.about_menu())
    await callback.answer()
