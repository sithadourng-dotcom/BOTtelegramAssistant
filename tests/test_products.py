"""Unit tests for product management and inventory limits."""

from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.user import User
from app.services.products import ProductService


@pytest.mark.asyncio
async def test_admin_create_product(db_session: AsyncSession, admin_user: User):
    service = ProductService(db_session)
    product = await service.create_product(
        actor=admin_user,
        name="Whitening Cream",
        sku="CREAM-01",
        category="Skincare",
        retail_price=Decimal("30.00"),
        wholesale_price=Decimal("20.00"),
        cost=Decimal("12.00"),
        stock_quantity=50,
        minimum_stock=10,
    )
    assert product.id is not None
    assert product.sku == "CREAM-01"
    assert product.retail_price == Decimal("30.00")
    assert product.is_low_stock is False


@pytest.mark.asyncio
async def test_duplicate_sku_rejected(db_session: AsyncSession, admin_user: User):
    service = ProductService(db_session)
    await service.create_product(
        actor=admin_user,
        name="Item A",
        sku="DUP-01",
        retail_price=Decimal("10.00"),
        cost=Decimal("5.00"),
    )

    with pytest.raises(ValueError, match="already exists"):
        await service.create_product(
            actor=admin_user,
            name="Item B",
            sku="dup-01",
            retail_price=Decimal("15.00"),
        )


@pytest.mark.asyncio
async def test_non_admin_cannot_create_product(db_session: AsyncSession, seller_user: User):
    service = ProductService(db_session)
    with pytest.raises(PermissionError):
        await service.create_product(
            actor=seller_user,
            name="Sneaky Item",
            sku="SNEAKY-1",
            retail_price=Decimal("5.00"),
        )


@pytest.mark.asyncio
async def test_low_stock_detection(db_session: AsyncSession, admin_user: User):
    service = ProductService(db_session)
    product = await service.create_product(
        actor=admin_user,
        name="Low Stock Item",
        sku="LOW-01",
        stock_quantity=5,
        minimum_stock=10,
    )
    assert product.is_low_stock is True

    low_items = await service.get_low_stock_products()
    assert len(low_items) == 1
    assert low_items[0].sku == "LOW-01"
