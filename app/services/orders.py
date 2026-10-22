"""Order service with server-side validation and inventory consistency."""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.database.models.product import Product
from app.database.models.user import User, UserRole
from app.database.repositories.order_repo import OrderRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.customer_repo import CustomerRepository
from app.database.repositories.audit_repo import AuditRepository
from app.database.repositories.sale_repo import SaleRepository
from app.services.users import has_permission
from app.utils.tz import now_tz, today_tz


class OrderService:
    """Service handling Order creation, stock consistency, and lifecycle."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.product_repo = ProductRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.audit_repo = AuditRepository(session)
        self.sale_repo = SaleRepository(session)

    async def create_order(
        self,
        actor: User,
        customer_id: int,
        items: List[Tuple[int, int]],  # List of (product_id, quantity)
        discount: Decimal = Decimal("0.00"),
        shipping_fee: Decimal = Decimal("0.00"),
        notes: Optional[str] = None,
        payment_status: PaymentStatus = PaymentStatus.UNPAID,
    ) -> Tuple[Order, List[Product]]:
        """
        Create order safely.
        Server verifies each product, gets official price/cost, validates stock,
        deducts stock, creates order and order items, and returns (order, low_stock_alerts).
        """
        if not has_permission(actor, UserRole.SELLER):
            raise PermissionError("Only Sellers, Managers, or Admins can create orders.")

        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist.")

        if not items:
            raise ValueError("Order must contain at least one product.")

        items_data: List[Tuple[int, int, Decimal, Decimal]] = []
        low_stock_products: List[Product] = []

        # Validate stock and gather prices from database
        for prod_id, qty in items:
            if qty <= 0:
                raise ValueError("Quantity must be greater than zero.")
            product = await self.product_repo.get_by_id(prod_id)
            if not product or not product.active:
                raise ValueError(f"Product ID {prod_id} is inactive or not found.")

            if product.stock_quantity < qty:
                raise ValueError(
                    f"Insufficient stock for '{product.name}'. Available: {product.stock_quantity}, requested: {qty}."
                )

            # Deduct stock
            product.stock_quantity -= qty
            if product.is_low_stock:
                low_stock_products.append(product)

            items_data.append((product.id, qty, product.retail_price, product.cost))

        # Create order
        order = await self.order_repo.create_order(
            customer_id=customer_id,
            seller_id=actor.id,
            items_data=items_data,
            discount=discount,
            shipping_fee=shipping_fee,
            notes=notes,
            payment_status=payment_status,
            order_status=OrderStatus.PAID if payment_status == PaymentStatus.PAID else OrderStatus.PENDING,
        )

        # Update customer metrics
        await self.customer_repo.update_stats(customer_id, order.total, order.created_at)

        # Record sales transactions for reporting
        for prod_id, qty, u_price, c_price in items_data:
            await self.sale_repo.record_sale(
                seller_id=actor.id,
                product_id=prod_id,
                quantity=qty,
                unit_price=u_price,
                cost_price=c_price,
                sale_date=today_tz(),
                customer_id=customer_id,
                order_id=order.id,
                notes=f"Order {order.order_number}",
            )

        await self.audit_repo.log_action(
            action="ORDER_CREATED",
            entity_type="Order",
            user_id=actor.id,
            entity_id=str(order.id),
            new_value=f"order_number={order.order_number}, total={order.total}, items={len(items_data)}",
        )

        return order, low_stock_products

    async def update_order_status(self, actor: User, order_id: int, new_status: OrderStatus) -> Optional[Order]:
        """Update order status and restore inventory if cancelled."""
        if not has_permission(actor, UserRole.MANAGER):
            raise PermissionError("Only Manager, Admin, or Owner can update order status.")

        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return None

        old_status = order.order_status
        if old_status == new_status:
            return order

        # If transitioning to CANCELLED, restore product stock
        if new_status == OrderStatus.CANCELLED and old_status != OrderStatus.CANCELLED:
            for item in order.items:
                await self.product_repo.update_stock(item.product_id, item.quantity)

        order.order_status = new_status
        await self.session.flush()

        await self.audit_repo.log_action(
            action="ORDER_STATUS_CHANGED",
            entity_type="Order",
            user_id=actor.id,
            entity_id=str(order.id),
            old_value=f"status={old_status.value}",
            new_value=f"status={new_status.value}",
        )
        return order

    async def update_payment_status(self, actor: User, order_id: int, payment_status: PaymentStatus) -> Optional[Order]:
        """Update payment status of an order."""
        if not has_permission(actor, UserRole.MANAGER):
            raise PermissionError("Only Manager, Admin, or Owner can update payment status.")

        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return None

        old_payment = order.payment_status
        order.payment_status = payment_status
        if payment_status == PaymentStatus.PAID and order.order_status == OrderStatus.PENDING:
            order.order_status = OrderStatus.PAID

        await self.session.flush()

        await self.audit_repo.log_action(
            action="ORDER_PAYMENT_CHANGED",
            entity_type="Order",
            user_id=actor.id,
            entity_id=str(order.id),
            old_value=f"payment={old_payment.value}",
            new_value=f"payment={payment_status.value}",
        )
        return order

    async def get_order(self, order_id: int) -> Optional[Order]:
        return await self.order_repo.get_by_id(order_id)

    async def get_by_order_number(self, order_number: str) -> Optional[Order]:
        return await self.order_repo.get_by_order_number(order_number)

    async def list_orders(
        self,
        seller_id: Optional[int] = None,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        limit: int = 50,
    ) -> Sequence[Order]:
        return await self.order_repo.list_orders(
            seller_id=seller_id,
            status=status,
            payment_status=payment_status,
            limit=limit,
        )
