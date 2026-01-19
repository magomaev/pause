from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import BigInteger, DateTime, String, Text, Boolean, Enum as SQLEnum, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now():
    """Текущее время в UTC."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ===== ENUM'ы для заказов =====

class OrderStatus(str, Enum):
    PENDING = "pending"          # Ожидает оплаты
    PAID = "paid"                # Оплачен (ожидает подтверждения)
    CONFIRMED = "confirmed"      # Подтверждён
    CANCELLED = "cancelled"      # Отменён


class BoxOrderStatus(str, Enum):
    PENDING = "pending"          # Ожидает оплаты
    PAID = "paid"                # Оплачен
    CONFIRMED = "confirmed"      # Подтверждён
    SHIPPED = "shipped"          # Отправлен
    DELIVERED = "delivered"      # Доставлен
    CANCELLED = "cancelled"      # Отменён


# ===== ENUM'ы для напоминаний =====

class ReminderFrequency(str, Enum):
    DAILY = "daily"              # Каждый день
    THREE_PER_WEEK = "3_per_week"  # 3 раза в неделю
    WEEKLY = "weekly"            # 1 раз в неделю


class ReminderTime(str, Enum):
    MORNING = "morning"          # 7-10
    AFTERNOON = "afternoon"      # 12-15
    EVENING = "evening"          # 18-21
    RANDOM = "random"            # 9-22


# ===== МОДЕЛИ =====

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Настройки онбординга и напоминаний
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_frequency: Mapped[ReminderFrequency | None] = mapped_column(
        SQLEnum(ReminderFrequency), nullable=True
    )
    reminder_time: Mapped[ReminderTime | None] = mapped_column(
        SQLEnum(ReminderTime), nullable=True
    )


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_status", "status"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_telegram_status", "telegram_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    amount: Mapped[int] = mapped_column(default=79)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BoxOrder(Base):
    """Предзаказ физического набора."""
    __tablename__ = "box_orders"
    __table_args__ = (
        Index("ix_box_orders_status", "status"),
        Index("ix_box_orders_box_month", "box_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)  # Полный адрес доставки
    box_month: Mapped[str] = mapped_column(String(7))  # Формат "2026-02"
    amount: Mapped[int] = mapped_column(default=79)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    status: Mapped[BoxOrderStatus] = mapped_column(
        SQLEnum(BoxOrderStatus), default=BoxOrderStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Reminder(Base):
    """Напоминания для рассылки контента."""
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # photo, video, audio
    media_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    target: Mapped[str] = mapped_column(String(50), default="all")  # all, paid, telegram_id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# ===== КЭШИРОВАНИЕ КОНТЕНТА ИЗ NOTION =====

class ContentCache(Base):
    """Кэш контента из Notion (паузы, ссылки)."""
    __tablename__ = "content_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_type: Mapped[str] = mapped_column(String(50), index=True)  # pause_short, pause_long, breathe, movie, book
    content: Mapped[str] = mapped_column(Text)
    notion_page_id: Mapped[str] = mapped_column(String(50), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UITextCache(Base):
    """Кэш UI текстов из Notion."""
    __tablename__ = "ui_text_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # ONBOARDING_WELCOME, etc.
    text: Mapped[str] = mapped_column(Text)
    notion_page_id: Mapped[str] = mapped_column(String(50))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
