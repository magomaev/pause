# P1-002: Race Condition (TOCTOU) в box_start

## Severity: P1 (Critical)

## Описание
В `handlers/box.py` есть проверка на дублирующийся заказ, но между проверкой и созданием заказа нет блокировки. При быстром двойном нажатии пользователь может создать два заказа на один месяц.

## Файл
`handlers/box.py` - функция `box_start`

## Проблема
```python
# 1. Проверяем наличие заказа (Time Of Check)
existing = await session.execute(select(BoxOrder).where(...))

# <-- Здесь другой запрос может создать заказ

# 2. Создаём заказ (Time Of Use)
order = BoxOrder(...)
session.add(order)
```

## Решение
Использовать `SELECT ... FOR UPDATE` или уникальный constraint:

### Вариант 1: Row-level locking
```python
async with get_session() as session:
    # Блокируем строку для этого пользователя
    await session.execute(
        select(BoxOrder)
        .where(BoxOrder.telegram_id == telegram_id, BoxOrder.box_month == month_key)
        .with_for_update(skip_locked=True)
    )

    # Теперь безопасно проверяем и создаём
    existing = await session.execute(...)
    if existing.scalar_one_or_none():
        return "already_exists"

    order = BoxOrder(...)
    session.add(order)
    await session.commit()
```

### Вариант 2: Unique constraint (рекомендуется)
```python
# В models.py добавить:
__table_args__ = (
    UniqueConstraint('telegram_id', 'box_month', 'status',
                     name='uq_box_order_user_month_active'),
)
```

## Влияние
- Без исправления: дублирующиеся заказы, путаница с оплатой
- С исправлением: гарантия одного активного заказа на месяц
