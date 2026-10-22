"""Order and OrderItem models with status enums."""

import enum
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base, TimestampMixin


class PaymentStatus(str, enum.Enum):
    """Payment progress status."""
    UNPAID = "UNPAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class OrderStatus(str, enum.Enum):
    """Order fulfillment status."""
    PENDING = "PENDING"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    SHIPPING = "SHIPPING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    @classmethod
    def get_badge(cls, status: "OrderStatus") -> str:
        badges = {
            cls.PENDING: "📝 Pending",
            cls.PAID: "💵 Paid",
            cls.PROCESSING: "📦 Processing",
            cls.SHIPPING: "🚚 Shipping",
            cls.COMPLETED: "✅ Completed",
            cls.CANCELLED: "❌ Cancelled",
        }
        return badges.get(status, status.value)


class Order(Base, TimestampMixin):
    """Customer sales order model."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    seller_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum", native_enum=False),
        default=PaymentStatus.UNPAID,
        nullable=False,
        index=True,
    )
    order_status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status_enum", native_enum=False),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", backref="orders", lazy="joined")
    seller: Mapped["User"] = relationship("User", foreign_keys=[seller_id], lazy="joined")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def calculate_totals(self) -> None:
        """Calculate subtotal and grand total server-side safely."""
        sub = sum((item.total_price for item in self.items), Decimal("0.00"))
        self.subtotal = sub
        disc = self.discount or Decimal("0.00")
        ship = self.shipping_fee or Decimal("0.00")
        self.total = max(Decimal("0.00"), sub - disc + ship)


class OrderItem(Base):
    """Line item in an order."""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="joined")

    def __repr__(self) -> str:
        return f"<OrderItem id={self.id} prod={self.product_id} qty={self.quantity} total={self.total_price}>"
