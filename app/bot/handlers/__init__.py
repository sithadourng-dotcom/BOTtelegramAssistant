"""Handlers package and router registration."""

from aiogram import Router

from app.bot.handlers.start import router as start_router
from app.bot.handlers.dashboard import router as dashboard_router
from app.bot.handlers.products import router as products_router
from app.bot.handlers.orders import router as orders_router
from app.bot.handlers.sales import router as sales_router
from app.bot.handlers.reports import router as reports_router
from app.bot.handlers.tasks import router as tasks_router
from app.bot.handlers.team import router as team_router
from app.bot.handlers.notifications import router as notifications_router
from app.bot.handlers.search import router as search_router
from app.bot.handlers.settings import router as settings_router
from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.ai_assistant import router as ai_assistant_router


def get_main_router() -> Router:
    """Consolidate all feature routers into a single master router."""
    main_router = Router(name="main_router")
    main_router.include_router(start_router)
    main_router.include_router(dashboard_router)
    main_router.include_router(products_router)
    main_router.include_router(orders_router)
    main_router.include_router(sales_router)
    main_router.include_router(reports_router)
    main_router.include_router(tasks_router)
    main_router.include_router(team_router)
    main_router.include_router(notifications_router)
    main_router.include_router(search_router)
    main_router.include_router(settings_router)
    main_router.include_router(admin_router)
    main_router.include_router(ai_assistant_router)
    return main_router
