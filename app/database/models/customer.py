"""Customer model."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    """Customer profile and CRM tracking model."""
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    seller_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    last_order_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship to user/seller
    seller: Mapped[Optional["User"]] = relationship("User", foreign_keys=[seller_id])

    @property
    def is_repeat_customer(self) -> bool:
        """A customer with 2 or more orders is a repeat customer."""
        return self.total_orders >= 2

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name='{self.name}' phone='{self.phone}' orders={self.total_orders}>"
