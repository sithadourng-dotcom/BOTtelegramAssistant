"""Sale model for tracking individual sales activities and profitability."""

from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base, TimestampMixin


class Sale(Base, TimestampMixin):
    """Direct or order-linked sales transaction."""
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    seller_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    sale_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    seller: Mapped["User"] = relationship("User", foreign_keys=[seller_id], lazy="joined")
    product: Mapped["Product"] = relationship("Product", foreign_keys=[product_id], lazy="joined")
    customer: Mapped[Optional["Customer"]] = relationship("Customer", foreign_keys=[customer_id], lazy="joined")
    order: Mapped[Optional["Order"]] = relationship("Order", foreign_keys=[order_id])

    @classmethod
    def calculate_metrics(cls, quantity: int, unit_price: Decimal, cost_price: Decimal) -> tuple[Decimal, Decimal, Decimal]:
        """Compute revenue, total cost, and gross profit."""
        revenue = (Decimal(str(quantity)) * unit_price).quantize(Decimal("0.01"))
        cost = (Decimal(str(quantity)) * cost_price).quantize(Decimal("0.01"))
        gross_profit = (revenue - cost).quantize(Decimal("0.01"))
        return revenue, cost, gross_profit

    def __repr__(self) -> str:
        return f"<Sale id={self.id} seller={self.seller_id} prod={self.product_id} rev={self.revenue} profit={self.gross_profit}>"
