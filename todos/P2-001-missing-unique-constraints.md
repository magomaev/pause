# P2-001: Отсутствуют уникальные constraints

## Severity: P2 (Important)

## Описание
В моделях `User`, `Order`, `BoxOrder` отсутствуют уникальные ограничения, которые должны гарантироваться на уровне БД.

## Файлы
`database/models.py`

## Проблемы

### 1. User.telegram_id не уникален на уровне БД
```python
telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
# Должно быть:
telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
```

### 2. Нет защиты от дублей BoxOrder
```python
__table_args__ = (
    # Добавить:
    UniqueConstraint(
        'telegram_id', 'box_month',
        name='uq_box_order_user_month',
        postgresql_where=text("status NOT IN ('CANCELLED')")
    ),
)
```

## Решение
Добавить constraints в models.py и создать миграцию:

```python
class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,  # <-- добавить
        index=True
    )

class BoxOrder(Base):
    __tablename__ = "box_orders"

    __table_args__ = (
        Index("ix_box_orders_telegram_status", "telegram_id", "status"),
        UniqueConstraint('telegram_id', 'box_month', name='uq_active_box_order'),
    )
```

## Влияние
- Без исправления: возможны дубли данных
- С исправлением: целостность данных на уровне БД
