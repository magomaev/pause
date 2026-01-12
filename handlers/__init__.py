from handlers.onboarding import router as onboarding_router
from handlers.pause import router as pause_router
from handlers.box import router as box_router
from handlers.orders import router as orders_router
from handlers.admin import router as admin_router

__all__ = [
    "onboarding_router",
    "pause_router",
    "box_router",
    "orders_router",
    "admin_router",
]
