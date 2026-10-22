"""Product repository for inventory database operations."""

from decimal import Decimal
from typing import Optional, Sequence
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.product import Product


class ProductRepository:
    """Repository handling Product database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, product_id: int) -> Optional[Product]:
        stmt = select(Product).where(Product.id == product_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> Optional[Product]:
        stmt = select(Product).where(Product.sku.ilike(sku.strip()))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_product(
        self,
        name: str,
        sku: str,
        category: str = "General",
        description: Optional[str] = None,
        retail_price: Decimal = Decimal("0.00"),
        wholesale_price: Decimal = Decimal("0.00"),
        cost: Decimal = Decimal("0.00"),
        stock_quantity: int = 0,
        minimum_stock: int = 10,
        image_url: Optional[str] = None,
        active: bool = True,
    ) -> Product:
        product = Product(
            name=name.strip(),
            sku=sku.strip().upper(),
            category=category.strip(),
            description=description,
            retail_price=retail_price,
            wholesale_price=wholesale_price,
            cost=cost,
            stock_quantity=stock_quantity,
            minimum_stock=minimum_stock,
            image_url=image_url,
            active=active,
        )
        self.session.add(product)
        await self.session.flush()
        return product

    async def list_products(
        self,
        category: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Product]:
        stmt = select(Product)
        if active_only:
            stmt = stmt.where(Product.active == True)
        if category:
            stmt = stmt.where(Product.category.ilike(category.strip()))
        stmt = stmt.order_by(Product.name.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_products(self, query: str, active_only: bool = True, limit: int = 20) -> Sequence[Product]:
        pattern = f"%{query.strip()}%"
        stmt = select(Product).where(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
                Product.category.ilike(pattern),
            )
        )
        if active_only:
            stmt = stmt.where(Product.active == True)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_stock(self, product_id: int, quantity_delta: int) -> Optional[Product]:
        product = await self.get_by_id(product_id)
        if product:
            product.stock_quantity = max(0, product.stock_quantity + quantity_delta)
            await self.session.flush()
        return product

    async def get_low_stock_products(self) -> Sequence[Product]:
        stmt = select(Product).where(
            Product.active == True,
            Product.stock_quantity <= Product.minimum_stock,
        ).order_by(Product.stock_quantity.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_all_categories(self) -> Sequence[str]:
        stmt = select(Product.category).where(Product.active == True).distinct()
        result = await self.session.execute(stmt)
        return result.scalars().all()
