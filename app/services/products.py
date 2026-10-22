"""Product service for business inventory management."""

from decimal import Decimal
from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.product import Product
from app.database.models.user import User, UserRole
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.audit_repo import AuditRepository
from app.services.users import has_permission


class ProductService:
    """Service handling Product CRUD and inventory controls."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.audit_repo = AuditRepository(session)

    async def create_product(
        self,
        actor: User,
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
    ) -> Product:
        if not has_permission(actor, UserRole.ADMIN):
            raise PermissionError("Only Admin or Owner can add products.")

        if retail_price < 0 or wholesale_price < 0 or cost < 0 or stock_quantity < 0:
            raise ValueError("Prices and stock quantity must be non-negative.")

        existing = await self.product_repo.get_by_sku(sku)
        if existing:
            raise ValueError(f"Product with SKU '{sku.upper()}' already exists.")

        product = await self.product_repo.create_product(
            name=name,
            sku=sku,
            category=category,
            description=description,
            retail_price=retail_price,
            wholesale_price=wholesale_price,
            cost=cost,
            stock_quantity=stock_quantity,
            minimum_stock=minimum_stock,
            image_url=image_url,
            active=True,
        )

        await self.audit_repo.log_action(
            action="PRODUCT_CREATED",
            entity_type="Product",
            user_id=actor.id,
            entity_id=str(product.id),
            new_value=f"sku={product.sku}, name={product.name}, price={product.retail_price}",
        )
        return product

    async def update_product(
        self,
        actor: User,
        product_id: int,
        name: Optional[str] = None,
        retail_price: Optional[Decimal] = None,
        wholesale_price: Optional[Decimal] = None,
        cost: Optional[Decimal] = None,
        stock_quantity: Optional[int] = None,
        minimum_stock: Optional[int] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Optional[Product]:
        if not has_permission(actor, UserRole.ADMIN):
            raise PermissionError("Only Admin or Owner can edit products.")

        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return None

        old_snapshot = f"name={product.name}, price={product.retail_price}, stock={product.stock_quantity}, active={product.active}"

        if name is not None:
            product.name = name.strip()
        if retail_price is not None:
            if retail_price < 0:
                raise ValueError("Retail price cannot be negative.")
            product.retail_price = retail_price
        if wholesale_price is not None:
            if wholesale_price < 0:
                raise ValueError("Wholesale price cannot be negative.")
            product.wholesale_price = wholesale_price
        if cost is not None:
            if cost < 0:
                raise ValueError("Cost cannot be negative.")
            product.cost = cost
        if stock_quantity is not None:
            if stock_quantity < 0:
                raise ValueError("Stock quantity cannot be negative.")
            product.stock_quantity = stock_quantity
        if minimum_stock is not None:
            product.minimum_stock = minimum_stock
        if category is not None:
            product.category = category.strip()
        if description is not None:
            product.description = description
        if image_url is not None:
            product.image_url = image_url
        if active is not None:
            product.active = active

        await self.session.flush()

        await self.audit_repo.log_action(
            action="PRODUCT_UPDATED",
            entity_type="Product",
            user_id=actor.id,
            entity_id=str(product.id),
            old_value=old_snapshot,
            new_value=f"name={product.name}, price={product.retail_price}, stock={product.stock_quantity}, active={product.active}",
        )
        return product

    async def get_product(self, product_id: int) -> Optional[Product]:
        return await self.product_repo.get_by_id(product_id)

    async def list_products(self, category: Optional[str] = None, active_only: bool = True) -> Sequence[Product]:
        return await self.product_repo.list_products(category=category, active_only=active_only)

    async def search_products(self, query: str) -> Sequence[Product]:
        return await self.product_repo.search_products(query=query)

    async def get_low_stock_products(self) -> Sequence[Product]:
        return await self.product_repo.get_low_stock_products()
