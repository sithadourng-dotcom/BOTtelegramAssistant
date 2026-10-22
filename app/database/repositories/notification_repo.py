"""Notification repository for storing broadcast alerts and reminders."""

from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.notification import Notification
from app.utils.tz import now_tz


class NotificationRepository:
    """Repository handling notification records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "ANNOUNCEMENT",
        sender_id: Optional[int] = None,
        target_role: Optional[str] = None,
        target_user_id: Optional[int] = None,
    ) -> Notification:
        notif = Notification(
            title=title.strip(),
            message=message.strip(),
            notification_type=notification_type.strip(),
            sender_id=sender_id,
            target_role=target_role,
            target_user_id=target_user_id,
            sent_at=now_tz(),
        )
        self.session.add(notif)
        await self.session.flush()
        return notif

    async def list_notifications(
        self,
        target_role: Optional[str] = None,
        target_user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Notification]:
        stmt = select(Notification)
        if target_user_id:
            stmt = stmt.where(Notification.target_user_id == target_user_id)
        if target_role:
            stmt = stmt.where(Notification.target_role == target_role)
        stmt = stmt.order_by(Notification.sent_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()
