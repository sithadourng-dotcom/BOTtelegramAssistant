"""Main application entry point with FastAPI, aiogram Dispatcher, and background jobs."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response, status
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update

from app.config import settings
from app.database.database import init_db, close_db
from app.bot.handlers import get_main_router
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.rate_limit import RateLimitMiddleware
from app.scheduler.jobs import setup_scheduler, scheduler
from app.utils.logger import logger
from app.utils.tz import now_tz


def create_bot() -> Bot:
    """Instantiate aiogram Bot with HTML default parse mode."""
    # If BOT_TOKEN is dummy or not set in dev, fallback token so the app still mounts for testing
    token = settings.BOT_TOKEN or "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Instantiate and configure aiogram Dispatcher with storage and middlewares."""
    if settings.REDIS_URL:
        try:
            from redis.asyncio import from_url
            redis_client = from_url(settings.REDIS_URL)
            storage = RedisStorage(redis=redis_client)
            logger.info("Using Redis for FSM state storage.")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis ({e}), falling back to MemoryStorage.")
            storage = MemoryStorage()
    else:
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    # Register Middlewares
    dp.message.middleware(RateLimitMiddleware(limit_per_sec=settings.RATE_LIMIT_PER_SECOND))
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Register Routers
    dp.include_router(get_main_router())

    return dp


bot = create_bot()
dp = create_dispatcher()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifecycle context manager."""
    logger.info("Starting Telegram Business Assistant Bot Application...")
    # 1. Initialize database tables
    await init_db()

    # 2. Start background scheduler
    job_scheduler = setup_scheduler(bot)
    job_scheduler.start()
    logger.info("Background job scheduler started.")

    # 3. Setup Webhook or Polling mode
    polling_task = None
    if settings.USE_WEBHOOK and settings.WEBHOOK_URL:
        webhook_target = f"{settings.WEBHOOK_URL.rstrip('/')}{settings.WEBHOOK_PATH}"
        logger.info(f"Setting Telegram webhook to: {webhook_target}")
        await bot.set_webhook(
            url=webhook_target,
            secret_token=settings.WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
    else:
        # If running via FastAPI but in polling mode, start polling in background
        logger.info("Starting bot in background Long-Polling mode...")
        polling_task = asyncio.create_task(dp.start_polling(bot, drop_pending_updates=True))

    yield

    # Shutdown sequence
    logger.info("Shutting down bot application...")
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

    if job_scheduler.running:
        job_scheduler.shutdown(wait=False)

    await bot.session.close()
    await close_db()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="Telegram Business Assistant Bot",
    description="Production-Ready Telegram Business Operating System API & Webhook Server",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Service health inspection endpoint."""
    return {
        "status": "healthy",
        "service": "telegram-business-assistant",
        "timestamp": now_tz().isoformat(),
        "timezone": settings.TIMEZONE,
        "scheduler_running": scheduler.running,
    }


@app.post(settings.WEBHOOK_PATH, tags=["Telegram Webhook"])
async def telegram_webhook(request: Request) -> Response:
    """Handle incoming updates pushed by Telegram Webhook."""
    if settings.WEBHOOK_SECRET:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret != settings.WEBHOOK_SECRET:
            return Response(status_code=status.HTTP_403_FORBIDDEN, content="Forbidden")

    payload = await request.json()
    update = Update.model_validate(payload, context={"bot": bot})
    await dp.feed_update(bot, update)
    return Response(status_code=status.HTTP_200_OK)


async def run_standalone_polling() -> None:
    """Run pure long-polling mode directly."""
    logger.info("Starting standalone long-polling mode...")
    await init_db()
    job_scheduler = setup_scheduler(bot)
    job_scheduler.start()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        if job_scheduler.running:
            job_scheduler.shutdown(wait=False)
        await bot.session.close()
        await close_db()


def main() -> None:
    """CLI runner."""
    if settings.USE_WEBHOOK:
        uvicorn.run(
            "app.main:app",
            host=settings.SERVER_HOST,
            port=settings.SERVER_PORT,
            log_level=settings.LOG_LEVEL.lower(),
        )
    else:
        # Run long polling directly
        asyncio.run(run_standalone_polling())


if __name__ == "__main__":
    main()
