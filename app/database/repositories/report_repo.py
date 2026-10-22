"""Daily report repository for operational submissions."""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.daily_report import DailyReport
from app.database.models.user import User, UserRole, UserStatus
from app.utils.tz import now_tz


class ReportRepository:
    """Repository handling DailyReport database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_and_date(self, user_id: int, report_date: date) -> Optional[DailyReport]:
        stmt = select(DailyReport).where(
            DailyReport.user_id == user_id,
            DailyReport.report_date == report_date,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def submit_or_update(
        self,
        user_id: int,
        report_date: date,
        sales_amount: Decimal = Decimal("0.00"),
        orders_count: int = 0,
        new_customers_count: int = 0,
        videos_posted: int = 0,
        messages_answered: int = 0,
        followups_count: int = 0,
        problems_faced: Optional[str] = None,
        tomorrow_goal: Optional[str] = None,
    ) -> DailyReport:
        existing = await self.get_by_user_and_date(user_id, report_date)
        if existing:
            existing.sales_amount = sales_amount
            existing.orders_count = orders_count
            existing.new_customers_count = new_customers_count
            existing.videos_posted = videos_posted
            existing.messages_answered = messages_answered
            existing.followups_count = followups_count
            existing.problems_faced = problems_faced
            existing.tomorrow_goal = tomorrow_goal
            existing.submitted_at = now_tz()
            await self.session.flush()
            return existing

        report = DailyReport(
            user_id=user_id,
            report_date=report_date,
            sales_amount=sales_amount,
            orders_count=orders_count,
            new_customers_count=new_customers_count,
            videos_posted=videos_posted,
            messages_answered=messages_answered,
            followups_count=followups_count,
            problems_faced=problems_faced,
            tomorrow_goal=tomorrow_goal,
            submitted_at=now_tz(),
        )
        self.session.add(report)
        await self.session.flush()
        return report

    async def list_reports(
        self,
        report_date: Optional[date] = None,
        user_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[DailyReport]:
        stmt = select(DailyReport)
        if report_date:
            stmt = stmt.where(DailyReport.report_date == report_date)
        if user_id:
            stmt = stmt.where(DailyReport.user_id == user_id)
        if start_date:
            stmt = stmt.where(DailyReport.report_date >= start_date)
        if end_date:
            stmt = stmt.where(DailyReport.report_date <= end_date)
        stmt = stmt.order_by(DailyReport.report_date.desc(), DailyReport.id.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_users_without_report(self, target_date: date) -> List[User]:
        """Find approved sellers and promoters who have not submitted a report for target_date."""
        submitted_subquery = select(DailyReport.user_id).where(DailyReport.report_date == target_date)
        stmt = select(User).where(
            User.role.in_([UserRole.SELLER, UserRole.PROMOTER, UserRole.LEADER]),
            User.status == UserStatus.APPROVED,
            User.is_active == True,
            User.id.notin_(submitted_subquery),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_reports_for_date(self, target_date: date) -> int:
        stmt = select(func.count(DailyReport.id)).where(DailyReport.report_date == target_date)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
