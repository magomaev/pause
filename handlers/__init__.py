from handlers.base import router as base_router
from handlers.orders import router as orders_router
from handlers.admin import router as admin_router

__all__ = ["base_router", "orders_router", "admin_router"]
