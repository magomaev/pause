# P3-002: Photo handler доступен всем пользователям

## Severity: P3 (Nice-to-have)

## Описание
Хэндлер `get_photo_file_id` в `onboarding.py` отвечает на любое фото и возвращает file_id. Это полезно для админа, но не нужно обычным пользователям.

## Файл
`handlers/onboarding.py:301-305`

## Текущий код
```python
@router.message(F.photo)
async def get_photo_file_id(message: Message):
    """Получить file_id фото (для настройки welcome photo)."""
    file_id = message.photo[-1].file_id
    await message.reply(f"`{file_id}`", parse_mode="Markdown")
```

## Решение
Ограничить только для админа или вынести в admin_router:

```python
# Вариант 1: проверка в хэндлере
@router.message(F.photo)
async def get_photo_file_id(message: Message, config: Config):
    if message.from_user.id != config.admin_id:
        return  # Игнорируем для обычных пользователей

    file_id = message.photo[-1].file_id
    await message.reply(f"`{file_id}`", parse_mode="Markdown")

# Вариант 2: перенести в admin_router с фильтром
@router.message(F.photo, AdminFilter())
async def get_photo_file_id(message: Message):
    ...
```

## Влияние
- Минимальное влияние на безопасность
- Улучшает UX (не путает пользователей ответами на фото)
