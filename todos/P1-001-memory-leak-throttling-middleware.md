# P1-001: Memory Leak в ThrottlingMiddleware

## Severity: P1 (Critical)

## Описание
`ThrottlingMiddleware._cache` растёт неограниченно. Каждый новый пользователь добавляет запись, которая никогда не удаляется. При длительной работе бота это приведёт к исчерпанию памяти.

## Файл
`middleware.py:14-21`

## Текущий код
```python
class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5, max_requests: int = 30, window: int = 60):
        self.rate_limit = rate_limit
        self.max_requests = max_requests
        self.window = window
        self._cache: Dict[int, Dict[str, float]] = defaultdict(
            lambda: {"last_request": 0.0, "request_count": 0, "window_start": 0.0}
        )
```

## Решение
Добавить TTL-based eviction или использовать `cachetools.TTLCache`:

```python
from cachetools import TTLCache

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5, max_requests: int = 30, window: int = 60):
        self.rate_limit = rate_limit
        self.max_requests = max_requests
        self.window = window
        # Автоматически удаляет записи через 10 минут неактивности
        self._cache: TTLCache = TTLCache(maxsize=10000, ttl=600)
```

## Зависимости
Добавить в requirements.txt: `cachetools>=5.0.0`

## Влияние
- Без исправления: OOM при большом количестве пользователей
- С исправлением: стабильное потребление памяти
