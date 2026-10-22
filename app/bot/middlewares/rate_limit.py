"""Rate limiting middleware to prevent spamming and abuse."""

import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from app.config import settings

USER_LAST_TIME: Dict[int, float] = {}


class RateLimitMiddleware(BaseMiddleware):
    """Simple sliding rate limiter per Telegram user ID."""

    def __init__(self, limit_per_sec: float = 2.0):
        self.limit_delay = 1.0 / limit_per_sec

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
            now = time.monotonic()
            last_time = USER_LAST_TIME.get(uid, 0.0)

            if now - last_time < self.limit_delay:
                # Silently ignore or answer warning
                return None

            USER_LAST_TIME[uid] = now

        return await handler(event, data)
