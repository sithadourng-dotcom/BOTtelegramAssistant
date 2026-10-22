"""Sales tracking and profit analysis service."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.product import Product
from app.database.models.sale import Sale
from app.database.models.user import User, UserRole
from app.database.repositories.audit_repo import AuditRepository
from app.database.repositories.customer_repo import CustomerRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.sale_repo import SaleRepository
from app.services.users import has_permission
from app.utils.tz import today_tz


class SaleService:
    """Service handling sales records and performance calculations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sale_repo = SaleRepository(session)
        self.product_repo = ProductRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.audit_repo = AuditRepository(session)

    async def record_quick_sale(
        self,
        actor: User,
        product_id: int,
        quantity: int,
        customer_id: Optional[int] = None,
        notes: Optional[str] = None,
        sale_date: Optional[date] = None,
    ) -> Tuple[Sale, Optional[Product]]:
        """
        Record a direct sale, calculate revenue, cost, and gross profit,
        deduct inventory stock, and return (sale, low_stock_product_alert).
        """
        if not has_permission(actor, UserRole.SELLER):
            raise PermissionError("Permission denied: You must be an approved seller.")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        product = await self.product_repo.get_by_id(product_id)
        if not product or not product.active:
            raise ValueError("Product not found or inactive.")

        if product.stock_quantity < quantity:
            raise ValueError(
                f"Insufficient stock for '{product.name}'. Available: {product.stock_quantity}, requested: {quantity}."
            )

        # Deduct stock
        product.stock_quantity -= quantity
        low_stock = product if product.is_low_stock else None

        current_date = sale_date or today_tz()
        sale = await self.sale_repo.record_sale(
            seller_id=actor.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.retail_price,
            cost_price=product.cost,
            sale_date=current_date,
            customer_id=customer_id,
            notes=notes,
        )

        # If customer given, update stats
        if customer_id:
            await self.customer_repo.update_stats(customer_id, sale.revenue, datetime.now())

        await self.audit_repo.log_action(
            action="SALE_RECORDED",
            entity_type="Sale",
            user_id=actor.id,
            entity_id=str(sale.id),
            new_value=f"product={product.name}, qty={quantity}, rev={sale.revenue}, profit={sale.gross_profit}",
        )

        return sale, low_stock

    async def get_summary_for_period(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        seller_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.sale_repo.get_summary(start_date=start_date, end_date=end_date, seller_id=seller_id)

    async def get_top_products(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 5,
    ) -> List[Tuple[str, int, Decimal]]:
        return await self.sale_repo.get_top_products(start_date=start_date, end_date=end_date, limit=limit)

    async def get_top_sellers(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 5,
    ) -> List[Tuple[str, Decimal, int]]:
        return await self.sale_repo.get_top_sellers(start_date=start_date, end_date=end_date, limit=limit)
