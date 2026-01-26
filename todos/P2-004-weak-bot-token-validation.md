# P2-004: Слабая валидация BOT_TOKEN

## Severity: P2 (Important)

## Описание
В `config.py` проверяется только наличие BOT_TOKEN, но не его формат. Ошибочный токен приведёт к непонятной ошибке от Telegram API вместо понятного сообщения при старте.

## Файл
`config.py`

## Текущий код
```python
if not config.bot_token:
    raise ValueError("BOT_TOKEN не установлен")
```

## Решение
Добавить валидацию формата токена:

```python
import re

def validate_bot_token(token: str) -> bool:
    """Валидация формата Telegram bot token."""
    # Формат: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
    pattern = r'^\d{8,10}:[A-Za-z0-9_-]{35}$'
    return bool(re.match(pattern, token))

# В load_config():
if not config.bot_token:
    raise ValueError("BOT_TOKEN не установлен")

if not validate_bot_token(config.bot_token):
    raise ValueError(
        "BOT_TOKEN имеет неверный формат. "
        "Ожидается: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    )
```

## Влияние
- Без исправления: непонятные ошибки при неверном токене
- С исправлением: ранняя диагностика проблемы
