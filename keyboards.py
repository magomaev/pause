from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import texts


# ===== ОНБОРДИНГ =====

def onboarding_welcome() -> InlineKeyboardMarkup:
    """Экран 0: приветствие."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_SETUP_PAUSE, callback_data="setup_pause")
    )
    return builder.as_markup()


def onboarding_reminders() -> InlineKeyboardMarkup:
    """Экран 1: нужны ли напоминания."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_YES, callback_data="reminders_yes"),
        InlineKeyboardButton(text=texts.BTN_NO, callback_data="reminders_no")
    )
    return builder.as_markup()


def onboarding_no_reminders() -> InlineKeyboardMarkup:
    """Экран 2A: без напоминаний."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_PAUSE_NOW, callback_data="pause_now")
    )
    return builder.as_markup()


def onboarding_frequency() -> InlineKeyboardMarkup:
    """Экран 2B: выбор частоты."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_FREQ_DAILY, callback_data="freq_daily")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_FREQ_3_WEEK, callback_data="freq_3_per_week")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_FREQ_WEEKLY, callback_data="freq_weekly")
    )
    return builder.as_markup()


def onboarding_time() -> InlineKeyboardMarkup:
    """Экран 3B: выбор времени."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_TIME_MORNING, callback_data="time_morning"),
        InlineKeyboardButton(text=texts.BTN_TIME_AFTERNOON, callback_data="time_afternoon")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_TIME_EVENING, callback_data="time_evening"),
        InlineKeyboardButton(text=texts.BTN_TIME_RANDOM, callback_data="time_random")
    )
    return builder.as_markup()


def onboarding_complete() -> InlineKeyboardMarkup:
    """Экран 4B: завершение настройки."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_PAUSE_NOW, callback_data="pause_now")
    )
    return builder.as_markup()


# ===== ПАУЗЫ =====

def pause_menu() -> InlineKeyboardMarkup:
    """Меню после паузы."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_PAUSE_NOW, callback_data="pause_now")
    )
    return builder.as_markup()


# ===== ПРЕДЗАКАЗ НАБОРА =====

def box_intro() -> InlineKeyboardMarkup:
    """Начало предзаказа набора."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_RESONATES, callback_data="box_start")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_LATER, callback_data="box_later")
    )
    return builder.as_markup()


def box_confirm_name() -> InlineKeyboardMarkup:
    """Подтверждение имени из Telegram."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_NAME_CORRECT, callback_data="box_name_ok")
    )
    return builder.as_markup()


def box_confirm() -> InlineKeyboardMarkup:
    """Подтверждение данных предзаказа."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_CONFIRM, callback_data="box_confirm")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="box_cancel")
    )
    return builder.as_markup()


def box_payment(payment_link: str) -> InlineKeyboardMarkup:
    """Оплата предзаказа набора."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_PAY, url=payment_link)
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_PAID, callback_data="box_paid")
    )
    return builder.as_markup()


def box_after_later() -> InlineKeyboardMarkup:
    """После 'вернуться позже'."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_PAUSE_NOW, callback_data="pause_now")
    )
    return builder.as_markup()


# ===== ЗАКАЗЫ (цифровой продукт) =====

def main_menu() -> InlineKeyboardMarkup:
    """Главное меню."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_ABOUT, callback_data="about")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_ORDER, callback_data="order")
    )
    return builder.as_markup()


def back_menu() -> InlineKeyboardMarkup:
    """Кнопка назад."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data="back")
    )
    return builder.as_markup()


def about_menu() -> InlineKeyboardMarkup:
    """Меню после 'О продукте'."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_ORDER, callback_data="order")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data="back")
    )
    return builder.as_markup()


def confirm_order() -> InlineKeyboardMarkup:
    """Подтверждение заказа."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_CONFIRM, callback_data="confirm_order")
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel_order")
    )
    return builder.as_markup()


def payment_menu(payment_link: str) -> InlineKeyboardMarkup:
    """Меню оплаты."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=texts.BTN_PAY, url=payment_link)
    )
    builder.row(
        InlineKeyboardButton(text=texts.BTN_PAID, callback_data="i_paid")
    )
    return builder.as_markup()


def admin_order_menu(order_id: int) -> InlineKeyboardMarkup:
    """Админское меню для заказа."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✓ Подтвердить", callback_data=f"confirm_{order_id}"),
        InlineKeyboardButton(text="✗ Отклонить", callback_data=f"reject_{order_id}")
    )
    return builder.as_markup()


def admin_box_order_menu(order_id: int) -> InlineKeyboardMarkup:
    """Админское меню для предзаказа набора."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✓ Подтвердить", callback_data=f"box_confirm_{order_id}"),
        InlineKeyboardButton(text="✗ Отклонить", callback_data=f"box_reject_{order_id}")
    )
    return builder.as_markup()


# ===== ГЛАВНОЕ МЕНЮ (Reply Keyboard) =====

def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Постоянное меню действий возле поля ввода."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=texts.BTN_MENU_PAUSE),
        KeyboardButton(text=texts.BTN_MENU_BREATHE)
    )
    builder.row(
        KeyboardButton(text=texts.BTN_MENU_MOVIE),
        KeyboardButton(text=texts.BTN_MENU_BOOK)
    )
    builder.row(
        KeyboardButton(text=texts.BTN_MENU_NEW_BOX),
        KeyboardButton(text=texts.BTN_MENU_SETTINGS)
    )
    return builder.as_markup(resize_keyboard=True)


def remove_reply_keyboard() -> ReplyKeyboardRemove:
    """Убрать reply keyboard."""
    return ReplyKeyboardRemove()
