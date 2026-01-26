# P2-003: N+1 Query Problem в /stats

## Severity: P2 (Important)

## Описание
Команда `/stats` выполняет 11 отдельных запросов к БД. При росте данных это будет замедлять ответ.

## Файл
`handlers/admin.py` - функция `cmd_stats`

## Текущий код
```python
# 11 отдельных запросов:
total_users = await session.scalar(select(func.count(User.id)))
with_reminders = await session.scalar(...)
total_orders = await session.scalar(...)
# ... и так далее
```

## Решение
Объединить в 2-3 запроса с использованием `CASE WHEN`:

```python
from sqlalchemy import case, func

async def get_stats(session):
    # Один запрос для User stats
    user_stats = await session.execute(
        select(
            func.count(User.id).label('total'),
            func.sum(case((User.reminder_enabled == True, 1), else_=0)).label('with_reminders'),
            func.sum(case((User.onboarding_completed == True, 1), else_=0)).label('completed_onboarding'),
        )
    )

    # Один запрос для Order stats
    order_stats = await session.execute(
        select(
            func.count(Order.id).label('total'),
            func.sum(case((Order.status == OrderStatus.PAID, 1), else_=0)).label('paid'),
            func.sum(case((Order.status == OrderStatus.CONFIRMED, 1), else_=0)).label('confirmed'),
            func.sum(case(
                (Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED]), Order.amount),
                else_=0
            )).label('revenue'),
        )
    )

    # Аналогично для BoxOrder
```

## Влияние
- Без исправления: медленный ответ при большом количестве данных
- С исправлением: O(1) вместо O(n) запросов
