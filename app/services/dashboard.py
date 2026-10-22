"""Dashboard service for real-time business statistics."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.sale_repo import SaleRepository
from app.database.repositories.order_repo import OrderRepository
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.activity_repo import ActivityRepository
from app.database.repositories.report_repo import ReportRepository
from app.utils.tz import today_tz


class DashboardService:
    """Service computing real-time business performance analytics."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sale_repo = SaleRepository(session)
        self.order_repo = OrderRepository(session)
        self.user_repo = UserRepository(session)
        self.activity_repo = ActivityRepository(session)
        self.report_repo = ReportRepository(session)

    def get_period_dates(self, period: str) -> Tuple[date, date, Optional[date], Optional[date]]:
        """
        Returns (start_date, end_date, prev_start, prev_end) for comparison.
        Supported periods: 'today', 'yesterday', 'this_week', 'this_month'.
        """
        today = today_tz()

        if period == "yesterday":
            start = today - timedelta(days=1)
            end = start
            prev_start = start - timedelta(days=1)
            prev_end = prev_start
        elif period == "this_week":
            # Monday of current week
            start = today - timedelta(days=today.weekday())
            end = today
            length = (end - start).days + 1
            prev_end = start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=length - 1)
        elif period == "this_month":
            start = today.replace(day=1)
            end = today
            prev_end = start - timedelta(days=1)
            prev_start = prev_end.replace(day=1)
        else:  # today
            start = today
            end = today
            prev_start = today - timedelta(days=1)
            prev_end = prev_start

        return start, end, prev_start, prev_end

    async def get_dashboard_metrics(self, period: str = "today") -> Dict[str, Any]:
        """Compute real business metrics for the specified timeframe."""
        start_date, end_date, prev_start, prev_end = self.get_period_dates(period)

        # Current period sales summary
        curr_sales = await self.sale_repo.get_summary(start_date=start_date, end_date=end_date)
        prev_sales = await self.sale_repo.get_summary(start_date=prev_start, end_date=prev_end) if prev_start else {}

        # Growth calculation
        curr_rev = float(curr_sales.get("revenue", Decimal("0.00")))
        prev_rev = float(prev_sales.get("revenue", Decimal("0.00")))
        if prev_rev > 0:
            growth_pct = ((curr_rev - prev_rev) / prev_rev) * 100.0
        elif curr_rev > 0:
            growth_pct = 100.0
        else:
            growth_pct = 0.0

        # Orders count in this period
        orders = await self.order_repo.list_orders(
            start_date=start_date,
            end_date=end_date + timedelta(days=1),
            limit=1000,
        )
        orders_count = len(orders)

        # Active sellers count
        active_sellers = await self.user_repo.count_active_sellers()

        # Content posted in this period
        content_types = ["tiktok_video", "facebook_post", "content_created", "live_session"]
        content_posted = 0
        cur_day = start_date
        while cur_day <= end_date:
            content_posted += await self.activity_repo.count_activities_for_date(cur_day, content_types)
            cur_day += timedelta(days=1)

        # Reports submitted in this period
        reports_count = 0
        cur_day = start_date
        while cur_day <= end_date:
            reports_count += await self.report_repo.count_reports_for_date(cur_day)
            cur_day += timedelta(days=1)

        # Month-to-date revenue & orders for summary footer
        month_start = today_tz().replace(day=1)
        month_summary = await self.sale_repo.get_summary(start_date=month_start, end_date=today_tz())

        # Top products
        top_products = await self.sale_repo.get_top_products(start_date=start_date, end_date=end_date, limit=3)

        return {
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "revenue": curr_sales.get("revenue", Decimal("0.00")),
            "cost": curr_sales.get("cost", Decimal("0.00")),
            "gross_profit": curr_sales.get("gross_profit", Decimal("0.00")),
            "units_sold": curr_sales.get("units_sold", 0),
            "orders_count": orders_count,
            "active_sellers": active_sellers,
            "content_posted": content_posted,
            "reports_submitted": reports_count,
            "growth_percent": round(growth_pct, 1),
            "month_revenue": month_summary.get("revenue", Decimal("0.00")),
            "month_orders": month_summary.get("sales_count", 0),
            "top_products": top_products,
        }
