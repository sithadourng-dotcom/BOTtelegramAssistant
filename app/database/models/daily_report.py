"""Daily report model."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base, TimestampMixin


class DailyReport(Base, TimestampMixin):
    """Daily operational report submitted by team members."""
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    sales_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    orders_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_customers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    videos_posted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages_answered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    followups_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    problems_faced: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tomorrow_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<DailyReport id={self.id} user={self.user_id} date={self.report_date} sales={self.sales_amount}>"
