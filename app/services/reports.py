"""Daily operational report submission and monitoring service."""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.daily_report import DailyReport
from app.database.models.user import User, UserRole
from app.database.repositories.report_repo import ReportRepository
from app.database.repositories.audit_repo import AuditRepository
from app.services.users import has_permission
from app.utils.tz import today_tz


class ReportService:
    """Service handling team daily report workflows."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.report_repo = ReportRepository(session)
        self.audit_repo = AuditRepository(session)

    async def submit_daily_report(
        self,
        actor: User,
        sales_amount: Decimal = Decimal("0.00"),
        orders_count: int = 0,
        new_customers_count: int = 0,
        videos_posted: int = 0,
        messages_answered: int = 0,
        followups_count: int = 0,
        problems_faced: Optional[str] = None,
        tomorrow_goal: Optional[str] = None,
        report_date: Optional[date] = None,
    ) -> DailyReport:
        if not has_permission(actor, UserRole.SELLER) and not has_permission(actor, UserRole.PROMOTER):
            raise PermissionError("Permission denied: You must be an approved team member.")

        target_date = report_date or today_tz()
        report = await self.report_repo.submit_or_update(
            user_id=actor.id,
            report_date=target_date,
            sales_amount=sales_amount,
            orders_count=orders_count,
            new_customers_count=new_customers_count,
            videos_posted=videos_posted,
            messages_answered=messages_answered,
            followups_count=followups_count,
            problems_faced=problems_faced,
            tomorrow_goal=tomorrow_goal,
        )

        await self.audit_repo.log_action(
            action="REPORT_SUBMITTED",
            entity_type="DailyReport",
            user_id=actor.id,
            entity_id=str(report.id),
            new_value=f"date={report.report_date}, sales={report.sales_amount}, orders={report.orders_count}",
        )
        return report

    async def get_user_report(self, user_id: int, report_date: Optional[date] = None) -> Optional[DailyReport]:
        target_date = report_date or today_tz()
        return await self.report_repo.get_by_user_and_date(user_id, target_date)

    async def list_reports(
        self,
        report_date: Optional[date] = None,
        user_id: Optional[int] = None,
    ) -> Sequence[DailyReport]:
        return await self.report_repo.list_reports(report_date=report_date, user_id=user_id)

    async def get_missing_reports(self, target_date: Optional[date] = None) -> List[User]:
        d = target_date or today_tz()
        return await self.report_repo.get_users_without_report(d)
