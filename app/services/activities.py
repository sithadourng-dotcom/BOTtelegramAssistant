"""Team activity logging service."""

from datetime import date
from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.activity import Activity
from app.database.models.user import User, UserRole
from app.database.repositories.activity_repo import ActivityRepository
from app.services.users import has_permission
from app.utils.tz import today_tz


class ActivityService:
    """Service handling team activity tracking."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.activity_repo = ActivityRepository(session)

    async def log_activity(
        self,
        actor: User,
        activity_type: str,
        quantity: int = 1,
        activity_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> Activity:
        if not has_permission(actor, UserRole.VIEWER):
            raise PermissionError("Permission denied.")

        act_date = activity_date or today_tz()
        return await self.activity_repo.log_activity(
            user_id=actor.id,
            activity_type=activity_type,
            quantity=quantity,
            activity_date=act_date,
            notes=notes,
        )

    async def list_activities(
        self,
        user_id: Optional[int] = None,
        activity_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Sequence[Activity]:
        return await self.activity_repo.list_activities(
            user_id=user_id,
            activity_type=activity_type,
            start_date=start_date,
            end_date=end_date,
        )

    async def count_content_posted(self, target_date: date) -> int:
        content_types = ["tiktok_video", "facebook_post", "content_created", "live_session"]
        return await self.activity_repo.count_activities_for_date(target_date, content_types)
