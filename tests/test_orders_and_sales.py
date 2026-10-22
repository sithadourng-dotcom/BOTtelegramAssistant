"""Unit tests for orders, stock deduction, and sales calculations."""

from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.order import OrderStatus
from app.database.models.user import User
from app.services.customers import CustomerService
from app.services.orders import OrderService
from app.services.products import ProductService
from app.services.sales import SaleService


@pytest.mark.asyncio
async def test_order_creation_and_server_side_calculation(
    db_session: AsyncSession,
    admin_user: User,
    seller_user: User,
):
    prod_service = ProductService(db_session)
    cust_service = CustomerService(db_session)
    order_service = OrderService(db_session)

    # 1. Create product
    prod = await prod_service.create_product(
        actor=admin_user,
        name="Sunscreen SPF 50",
        sku="SUN-01",
        retail_price=Decimal("20.00"),
        wholesale_price=Decimal("15.00"),
        cost=Decimal("8.00"),
        stock_quantity=50,
        minimum_stock=10,
    )

    # 2. Create customer
    cust = await cust_service.get_or_create_customer(
        actor=seller_user,
        name="Mary Johnson",
        phone="+85599887766",
    )

    # 3. Create order: 3 units @ $20 = $60 subtotal, -$5 discount, +$2 shipping => $57.00
    order, low_stock = await order_service.create_order(
        actor=seller_user,
        customer_id=cust.id,
        items=[(prod.id, 3)],
        discount=Decimal("5.00"),
        shipping_fee=Decimal("2.00"),
    )

    assert order.id is not None
    assert order.subtotal == Decimal("60.00")
    assert order.discount == Decimal("5.00")
    assert order.shipping_fee == Decimal("2.00")
    assert order.total == Decimal("57.00")

    # Verify inventory was deducted: 50 - 3 = 47
    reloaded_prod = await prod_service.get_product(prod.id)
    assert reloaded_prod.stock_quantity == 47


@pytest.mark.asyncio
async def test_insufficient_stock_raises_error(
    db_session: AsyncSession,
    admin_user: User,
    seller_user: User,
):
    prod_service = ProductService(db_session)
    cust_service = CustomerService(db_session)
    order_service = OrderService(db_session)

    prod = await prod_service.create_product(
        actor=admin_user,
        name="Limited Serum",
        sku="SERUM-01",
        retail_price=Decimal("40.00"),
        stock_quantity=2,
    )
    cust = await cust_service.get_or_create_customer(
        actor=seller_user,
        name="John Client",
        phone="+85512345678",
    )

    with pytest.raises(ValueError, match="Insufficient stock"):
        await order_service.create_order(
            actor=seller_user,
            customer_id=cust.id,
            items=[(prod.id, 5)],  # requests 5 but only 2 available
        )


@pytest.mark.asyncio
async def test_cancelling_order_restores_stock(
    db_session: AsyncSession,
    admin_user: User,
    seller_user: User,
):
    prod_service = ProductService(db_session)
    cust_service = CustomerService(db_session)
    order_service = OrderService(db_session)

    prod = await prod_service.create_product(
        actor=admin_user,
        name="Facial Cleanser",
        sku="CLEAN-01",
        retail_price=Decimal("15.00"),
        stock_quantity=20,
    )
    cust = await cust_service.get_or_create_customer(actor=seller_user, name="Lisa", phone="+85511000111")

    order, _ = await order_service.create_order(
        actor=seller_user,
        customer_id=cust.id,
        items=[(prod.id, 4)],
    )
    assert prod.stock_quantity == 16

    # Cancel order
    await order_service.update_order_status(actor=admin_user, order_id=order.id, new_status=OrderStatus.CANCELLED)
    reloaded_prod = await prod_service.get_product(prod.id)
    assert reloaded_prod.stock_quantity == 20  # Restored!


@pytest.mark.asyncio
async def test_sale_metrics_calculation(
    db_session: AsyncSession,
    admin_user: User,
    seller_user: User,
):
    prod_service = ProductService(db_session)
    sale_service = SaleService(db_session)

    prod = await prod_service.create_product(
        actor=admin_user,
        name="Herbal Tea",
        sku="TEA-01",
        retail_price=Decimal("12.50"),
        cost=Decimal("4.50"),
        stock_quantity=100,
    )

    sale, low_stock = await sale_service.record_quick_sale(
        actor=seller_user,
        product_id=prod.id,
        quantity=4,
    )

    # 4 * 12.50 = 50.00 revenue
    # 4 * 4.50 = 18.00 cost
    # 50.00 - 18.00 = 32.00 profit
    assert sale.revenue == Decimal("50.00")
    assert sale.cost == Decimal("18.00")
    assert sale.gross_profit == Decimal("32.00")
    assert prod.stock_quantity == 96
