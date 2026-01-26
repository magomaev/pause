# P1-003: Неполная конфигурация пула соединений БД

## Severity: P1 (Critical)

## Описание
В `database/connection.py` для PostgreSQL не настроены важные параметры пула: `pool_size`, `max_overflow`, `pool_recycle`. Это может привести к исчерпанию соединений под нагрузкой.

## Файл
`database/connection.py:18-25`

## Текущий код
```python
is_sqlite = "sqlite" in database_url
if not is_sqlite:
    engine_kwargs["pool_pre_ping"] = True  # Только это!
```

## Решение
```python
is_sqlite = "sqlite" in database_url

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 5,           # Базовый размер пула
        "max_overflow": 10,       # Дополнительные соединения при пике
        "pool_recycle": 1800,     # Переподключение каждые 30 мин
        "pool_timeout": 30,       # Таймаут ожидания соединения
    })
```

## Влияние
- Без исправления: "too many connections" при нагрузке
- С исправлением: стабильная работа под нагрузкой
