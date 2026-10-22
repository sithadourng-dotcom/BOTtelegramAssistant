"""Product model."""

from decimal import Decimal
from typing import Optional
from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    """Business product inventory model."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(128), default="General", nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retail_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    wholesale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minimum_stock: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    @property
    def is_low_stock(self) -> bool:
        """Check if stock is below or at minimum stock threshold."""
        return self.stock_quantity <= self.minimum_stock

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku='{self.sku}' name='{self.name}' stock={self.stock_quantity}>"
