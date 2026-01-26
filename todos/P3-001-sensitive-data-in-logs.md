# P3-001: Чувствительные данные в логах

## Severity: P3 (Nice-to-have)

## Описание
В логах выводятся username и telegram_id пользователей. При утечке логов это может быть проблемой приватности.

## Файлы
- `handlers/onboarding.py:80` - `logger.info(f"/start from user {message.from_user.id} (@{message.from_user.username})")`
- `handlers/box.py` - аналогичные логи

## Решение
Использовать хеширование или частичную маскировку:

```python
def mask_user(telegram_id: int, username: str | None) -> str:
    """Маскировка данных пользователя для логов."""
    masked_id = f"{str(telegram_id)[:3]}***{str(telegram_id)[-2:]}"
    if username:
        masked_name = f"@{username[:2]}***"
    else:
        masked_name = "no_username"
    return f"user {masked_id} ({masked_name})"

# Использование:
logger.info(f"/start from {mask_user(message.from_user.id, message.from_user.username)}")
# Вывод: "/start from user 123***89 (@al***)"
```

## Влияние
- Минимальное влияние на безопасность
- Улучшает compliance с GDPR
