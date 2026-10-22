"""Activity repository for tracking operational and promotional activities."""

from datetime import date
from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.activity import Activity


class ActivityRepository:
    """Repository handling Activity logging and statistics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_activity(
        self,
        user_id: int,
        activity_type: str,
        quantity: int = 1,
        activity_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> Activity:
        from app.utils.tz import today_tz
        act_date = activity_date or today_tz()
        activity = Activity(
            user_id=user_id,
            activity_type=activity_type.strip(),
            quantity=quantity,
            activity_date=act_date,
            notes=notes,
        )
        self.session.add(activity)
        await self.session.flush()
        return activity

    async def list_activities(
        self,
        user_id: Optional[int] = None,
        activity_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Activity]:
        stmt = select(Activity)
        if user_id:
            stmt = stmt.where(Activity.user_id == user_id)
        if activity_type:
            stmt = stmt.where(Activity.activity_type == activity_type)
        if start_date:
            stmt = stmt.where(Activity.activity_date >= start_date)
        if end_date:
            stmt = stmt.where(Activity.activity_date <= end_date)
        stmt = stmt.order_by(Activity.activity_date.desc(), Activity.id.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_activities_for_date(self, target_date: date, types: Optional[list[str]] = None) -> int:
        stmt = select(func.coalesce(func.sum(Activity.quantity), 0)).where(Activity.activity_date == target_date)
        if types:
            stmt = stmt.where(Activity.activity_type.in_(types))
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)
