"""Sale repository for recording sales transactions and business metrics."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.product import Product
from app.database.models.sale import Sale
from app.database.models.user import User


class SaleRepository:
    """Repository handling direct and order sales records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, sale_id: int) -> Optional[Sale]:
        stmt = select(Sale).where(Sale.id == sale_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def record_sale(
        self,
        seller_id: int,
        product_id: int,
        quantity: int,
        unit_price: Decimal,
        cost_price: Decimal,
        sale_date: date,
        customer_id: Optional[int] = None,
        order_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Sale:
        revenue, cost, gross_profit = Sale.calculate_metrics(quantity, unit_price, cost_price)
        sale = Sale(
            seller_id=seller_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            cost_price=cost_price,
            revenue=revenue,
            cost=cost,
            gross_profit=gross_profit,
            sale_date=sale_date,
            customer_id=customer_id,
            order_id=order_id,
            notes=notes,
        )
        self.session.add(sale)
        await self.session.flush()
        return sale

    async def list_sales(
        self,
        seller_id: Optional[int] = None,
        product_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Sale]:
        stmt = select(Sale)
        if seller_id:
            stmt = stmt.where(Sale.seller_id == seller_id)
        if product_id:
            stmt = stmt.where(Sale.product_id == product_id)
        if customer_id:
            stmt = stmt.where(Sale.customer_id == customer_id)
        if start_date:
            stmt = stmt.where(Sale.sale_date >= start_date)
        if end_date:
            stmt = stmt.where(Sale.sale_date <= end_date)
        stmt = stmt.order_by(Sale.sale_date.desc(), Sale.id.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        seller_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Aggregate revenue, cost, profit, total units, and sales count."""
        stmt = select(
            func.coalesce(func.sum(Sale.revenue), Decimal("0.00")),
            func.coalesce(func.sum(Sale.cost), Decimal("0.00")),
            func.coalesce(func.sum(Sale.gross_profit), Decimal("0.00")),
            func.coalesce(func.sum(Sale.quantity), 0),
            func.count(Sale.id),
        )
        if start_date:
            stmt = stmt.where(Sale.sale_date >= start_date)
        if end_date:
            stmt = stmt.where(Sale.sale_date <= end_date)
        if seller_id:
            stmt = stmt.where(Sale.seller_id == seller_id)

        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "revenue": row[0],
            "cost": row[1],
            "gross_profit": row[2],
            "units_sold": row[3],
            "sales_count": row[4],
        }

    async def get_top_products(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 5,
    ) -> List[Tuple[str, int, Decimal]]:
        """Return top products by units sold: list of (product_name, units, revenue)."""
        stmt = (
            select(
                Product.name,
                func.sum(Sale.quantity).label("total_units"),
                func.sum(Sale.revenue).label("total_rev"),
            )
            .join(Product, Sale.product_id == Product.id)
            .group_by(Product.name)
            .order_by(desc("total_units"))
            .limit(limit)
        )
        if start_date:
            stmt = stmt.where(Sale.sale_date >= start_date)
        if end_date:
            stmt = stmt.where(Sale.sale_date <= end_date)

        result = await self.session.execute(stmt)
        return [(row[0], int(row[1]), Decimal(str(row[2]))) for row in result.all()]

    async def get_top_sellers(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 5,
    ) -> List[Tuple[str, Decimal, int]]:
        """Return top sellers by revenue: list of (seller_name, revenue, units)."""
        stmt = (
            select(
                User.full_name,
                func.sum(Sale.revenue).label("total_rev"),
                func.sum(Sale.quantity).label("total_units"),
            )
            .join(User, Sale.seller_id == User.id)
            .group_by(User.full_name)
            .order_by(desc("total_rev"))
            .limit(limit)
        )
        if start_date:
            stmt = stmt.where(Sale.sale_date >= start_date)
        if end_date:
            stmt = stmt.where(Sale.sale_date <= end_date)

        result = await self.session.execute(stmt)
        return [(row[0], Decimal(str(row[1])), int(row[2])) for row in result.all()]
