"""
Планировщик напоминаний — автоматическая отправка пауз.
"""
import random
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select

import keyboards
from database import get_session, User, ReminderFrequency, ReminderTime
from content import ContentManager

logger = logging.getLogger(__name__)


# Временные диапазоны (час UTC)
TIME_RANGES = {
    ReminderTime.MORNING: (7, 10),      # 7:00 - 9:59
    ReminderTime.AFTERNOON: (12, 15),   # 12:00 - 14:59
    ReminderTime.EVENING: (18, 21),     # 18:00 - 20:59
    ReminderTime.RANDOM: (9, 22),       # 9:00 - 21:59
}

# Дни недели для 3 раза в неделю (Пн, Ср, Пт)
THREE_PER_WEEK_DAYS = {0, 2, 4}  # Monday, Wednesday, Friday


class PauseScheduler:
    """Планировщик для автоматической отправки напоминаний."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Запуск планировщика."""
        # Проверка каждый час в начале часа
        self.scheduler.add_job(
            self.check_and_send_pauses,
            CronTrigger(minute=0),
            id="pause_check",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("Pause scheduler started")

    def stop(self):
        """Остановка планировщика."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Pause scheduler stopped")

    async def check_and_send_pauses(self):
        """Проверить и отправить напоминания пользователям."""
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        current_weekday = now.weekday()  # 0 = Monday

        logger.debug(f"Checking pauses at {now}, hour={current_hour}, weekday={current_weekday}")

        # Получаем пользователей с включёнными напоминаниями
        async with get_session() as session:
            result = await session.execute(
                select(User).where(
                    User.reminder_enabled == True,  # noqa: E712
                    User.onboarding_completed == True  # noqa: E712
                )
            )
            users = result.scalars().all()

        sent_count = 0
        for user in users:
            if self._should_send_to_user(user, current_hour, current_weekday):
                success = await self._send_pause(user.telegram_id)
                if success:
                    sent_count += 1

        if sent_count > 0:
            logger.info(f"Sent {sent_count} pause reminders at hour {current_hour}")

    def _should_send_to_user(
        self,
        user: User,
        current_hour: int,
        current_weekday: int
    ) -> bool:
        """Проверить, нужно ли отправлять напоминание пользователю."""
        if not user.reminder_frequency or not user.reminder_time:
            return False

        # Проверка частоты
        if user.reminder_frequency == ReminderFrequency.WEEKLY:
            # Только по понедельникам
            if current_weekday != 0:
                return False
        elif user.reminder_frequency == ReminderFrequency.THREE_PER_WEEK:
            # Только Пн, Ср, Пт
            if current_weekday not in THREE_PER_WEEK_DAYS:
                return False
        # DAILY — каждый день, проверка не нужна

        # Проверка времени
        time_range = TIME_RANGES.get(user.reminder_time)
        if not time_range:
            return False

        start_hour, end_hour = time_range

        if user.reminder_time == ReminderTime.RANDOM:
            # Для случайного времени — отправляем в случайный час из диапазона
            # Используем telegram_id как seed для консистентности в пределах дня
            random.seed(user.telegram_id + current_weekday * 100 + datetime.now(timezone.utc).day)
            target_hour = random.randint(start_hour, end_hour - 1)
            random.seed()  # Сбрасываем seed

            return current_hour == target_hour
        else:
            # Для фиксированного времени — отправляем в начале диапазона
            return current_hour == start_hour

    async def _send_pause(self, telegram_id: int) -> bool:
        """Отправить паузу пользователю — короткая фраза."""
        content = ContentManager.get_instance()
        pause_text = await content.get_random_reminder()

        try:
            await self.bot.send_message(
                telegram_id,
                pause_text,
                reply_markup=keyboards.pause_menu()
            )
            return True
        except TelegramAPIError as e:
            logger.warning(f"Failed to send pause to {telegram_id}: {e}")
            return False


def create_scheduler(bot: Bot) -> PauseScheduler:
    """Создать экземпляр планировщика."""
    return PauseScheduler(bot)
