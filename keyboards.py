from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import texts


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_ABOUT, callback_data="about")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_ORDER, callback_data="order")
    )
    return builder.as_markup()


def back_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data="back")
    )
    return builder.as_markup()


def about_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_ORDER, callback_data="order")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data="back")
    )
    return builder.as_markup()


def confirm_order() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_CONFIRM, callback_data="confirm_order")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel_order")
    )
    return builder.as_markup()


def payment_menu(payment_link: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_PAY, url=payment_link)
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_PAID, callback_data="i_paid")
    )
    return builder.as_markup()


def admin_order_menu(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✓ Подтвердить", callback_data=f"confirm_{order_id}"),
        InlineKeyboardButton(text="✗ Отклонить", callback_data=f"reject_{order_id}")
    )
    return builder.as_markup()
