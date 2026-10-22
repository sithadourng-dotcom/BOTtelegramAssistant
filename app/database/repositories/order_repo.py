"""Order repository for order management database operations."""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.utils.tz import now_tz


class OrderRepository:
    """Repository handling Order and OrderItem database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items).joinedload(OrderItem.product))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_order_number(self, order_number: str) -> Optional[Order]:
        stmt = (
            select(Order)
            .where(Order.order_number == order_number.strip())
            .options(selectinload(Order.items).joinedload(OrderItem.product))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_order_number(self) -> str:
        """Generate human-readable unique order number: ORD-YYYYMMDD-XXXX."""
        today_str = now_tz().strftime("%Y%m%d")
        prefix = f"ORD-{today_str}-"
        stmt = select(func.count(Order.id)).where(Order.order_number.like(f"{prefix}%"))
        result = await self.session.execute(stmt)
        count = (result.scalar() or 0) + 1
        return f"{prefix}{count:04d}"

    async def create_order(
        self,
        customer_id: int,
        seller_id: int,
        items_data: List[Tuple[int, int, Decimal, Decimal]],  # (product_id, quantity, unit_price, cost_price)
        discount: Decimal = Decimal("0.00"),
        shipping_fee: Decimal = Decimal("0.00"),
        notes: Optional[str] = None,
        payment_status: PaymentStatus = PaymentStatus.UNPAID,
        order_status: OrderStatus = OrderStatus.PENDING,
    ) -> Order:
        order_number = await self.generate_order_number()
        order = Order(
            order_number=order_number,
            customer_id=customer_id,
            seller_id=seller_id,
            discount=discount,
            shipping_fee=shipping_fee,
            payment_status=payment_status,
            order_status=order_status,
            notes=notes,
        )
        self.session.add(order)
        await self.session.flush()

        # Add line items
        subtotal = Decimal("0.00")
        for prod_id, qty, u_price, c_price in items_data:
            line_total = (Decimal(str(qty)) * u_price).quantize(Decimal("0.01"))
            item = OrderItem(
                order_id=order.id,
                product_id=prod_id,
                quantity=qty,
                unit_price=u_price,
                cost_price=c_price,
                total_price=line_total,
            )
            self.session.add(item)
            subtotal += line_total

        order.subtotal = subtotal
        order.total = max(Decimal("0.00"), subtotal - discount + shipping_fee)
        await self.session.flush()
        return order

    async def list_orders(
        self,
        seller_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Order]:
        stmt = select(Order).options(selectinload(Order.items).joinedload(OrderItem.product))
        if seller_id:
            stmt = stmt.where(Order.seller_id == seller_id)
        if customer_id:
            stmt = stmt.where(Order.customer_id == customer_id)
        if status:
            stmt = stmt.where(Order.order_status == status)
        if payment_status:
            stmt = stmt.where(Order.payment_status == payment_status)
        if start_date:
            stmt = stmt.where(Order.created_at >= start_date)
        if end_date:
            stmt = stmt.where(Order.created_at <= end_date)
        stmt = stmt.order_by(Order.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_status(self, order_id: int, status: OrderStatus) -> Optional[Order]:
        order = await self.get_by_id(order_id)
        if order:
            order.order_status = status
            await self.session.flush()
        return order

    async def update_payment_status(self, order_id: int, status: PaymentStatus) -> Optional[Order]:
        order = await self.get_by_id(order_id)
        if order:
            order.payment_status = status
            if status == PaymentStatus.PAID and order.order_status == OrderStatus.PENDING:
                order.order_status = OrderStatus.PAID
            await self.session.flush()
        return order

    async def count_pending_orders(self) -> int:
        stmt = select(func.count(Order.id)).where(Order.order_status == OrderStatus.PENDING)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
