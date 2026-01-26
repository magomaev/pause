# P3-003: Magic Numbers в коде

## Severity: P3 (Nice-to-have)

## Описание
В коде встречаются "магические числа" без объяснения. Это затрудняет понимание и поддержку кода.

## Примеры

### scheduler.py:66
```python
batch_size = 100  # Почему 100?
```

### scheduler.py:96
```python
await asyncio.sleep(0.1)  # Почему 0.1 секунды?
```

### texts.py:152
```python
79 €  # Почему 79? Где определяется цена?
```

### box.py (calculate_box_month)
```python
if today.day <= 20:  # Почему 20?
    target = today.replace(day=1) + timedelta(days=32)  # Почему 32?
```

## Решение
Вынести в константы с понятными именами:

```python
# config.py или constants.py
SCHEDULER_BATCH_SIZE = 100  # Пользователей за один батч
SCHEDULER_BATCH_DELAY = 0.1  # Секунд между батчами (rate limit Telegram API)
BOX_PRICE_EUR = 79
BOX_ORDER_CUTOFF_DAY = 20  # До этого дня месяца можно заказать на следующий месяц
```

## Влияние
- Улучшает читаемость кода
- Упрощает изменение параметров
