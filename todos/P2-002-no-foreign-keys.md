# P2-002: Отсутствуют Foreign Keys

## Severity: P2 (Important)

## Описание
Модели `Order` и `BoxOrder` хранят `telegram_id`, но не имеют foreign key на `User`. Это может привести к orphaned records при удалении пользователя.

## Файл
`database/models.py`

## Текущий код
```python
class Order(Base):
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    # Нет связи с User

class BoxOrder(Base):
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    # Нет связи с User
```

## Решение
```python
class User(Base):
    __tablename__ = "users"

    # Добавить relationships
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    box_orders: Mapped[list["BoxOrder"]] = relationship(back_populates="user")


class Order(Base):
    __tablename__ = "orders"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    user: Mapped["User"] = relationship(back_populates="orders")

    # telegram_id оставить для быстрого доступа (денормализация)


class BoxOrder(Base):
    __tablename__ = "box_orders"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    user: Mapped["User"] = relationship(back_populates="box_orders")
```

## Миграция
Потребуется миграция для добавления колонки `user_id` и заполнения её из `telegram_id`.

## Влияние
- Без исправления: orphaned records, сложные JOIN-запросы
- С исправлением: referential integrity, удобные relationship queries
