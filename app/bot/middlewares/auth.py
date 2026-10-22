"""Authentication and user session injection middleware."""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.database import async_session_factory
from app.database.models.user import User, UserRole, UserStatus
from app.database.repositories.user_repo import UserRepository
from app.utils.logger import logger


class AuthMiddleware(BaseMiddleware):
    """Middleware that injects database session and authenticated User into handler context."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        from_user = None
        if isinstance(event, Message):
            from_user = event.from_user
        elif isinstance(event, CallbackQuery):
            from_user = event.from_user

        if not from_user:
            return await handler(event, data)

        async with async_session_factory() as session:
            data["session"] = session
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(from_user.id)

            # Auto-promote owner if telegram_id matches ADMIN_TELEGRAM_ID
            if from_user.id == settings.ADMIN_TELEGRAM_ID:
                if user and (user.role != UserRole.OWNER or user.status != UserStatus.APPROVED):
                    user.role = UserRole.OWNER
                    user.status = UserStatus.APPROVED
                    await session.commit()
                elif not user:
                    user = await user_repo.create_user(
                        telegram_id=from_user.id,
                        full_name=from_user.full_name or "Owner",
                        username=from_user.username,
                        role=UserRole.OWNER,
                        status=UserStatus.APPROVED,
                    )
                    await session.commit()

            data["user"] = user

            # Allow /start and cancel commands even if not registered
            if isinstance(event, Message) and event.text:
                cmd = event.text.strip().split()[0].lower()
                if cmd in ["/start", "❌ cancel", "/cancel"]:
                    return await handler(event, data)

            # Check status for registered users
            if user:
                if user.status == UserStatus.PENDING:
                    if isinstance(event, Message):
                        await event.answer(
                            "⏳ <b>Account Pending Approval</b>\n\n"
                            "Your registration request has been submitted to the Admin/Owner.\n"
                            "You will receive a notification once your account is approved.",
                            parse_mode="HTML",
                        )
                    elif isinstance(event, CallbackQuery):
                        await event.answer("Your account is pending admin approval.", show_alert=True)
                    return None
                elif user.status in (UserStatus.REJECTED, UserStatus.SUSPENDED):
                    if isinstance(event, Message):
                        await event.answer(
                            "🚫 <b>Access Restricted</b>\n\n"
                            "Your account is inactive or has been rejected. Please contact the administrator.",
                            parse_mode="HTML",
                        )
                    elif isinstance(event, CallbackQuery):
                        await event.answer("Access restricted.", show_alert=True)
                    return None

            return await handler(event, data)
