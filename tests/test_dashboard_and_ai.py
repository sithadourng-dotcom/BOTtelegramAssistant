"""Unit tests for dashboard statistics and AI assistant safe dispatch."""

from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.user import User
from app.services.ai_assistant import AIAssistantService
from app.services.dashboard import DashboardService
from app.services.products import ProductService
from app.services.sales import SaleService
from app.utils.tz import today_tz


@pytest.mark.asyncio
async def test_dashboard_metrics_with_real_data(
    db_session: AsyncSession,
    admin_user: User,
    seller_user: User,
):
    prod_service = ProductService(db_session)
    sale_service = SaleService(db_session)
    dash_service = DashboardService(db_session)

    # Add product and record sale
    prod = await prod_service.create_product(
        actor=admin_user,
        name="Organic Coffee",
        sku="COFFEE-01",
        retail_price=Decimal("15.00"),
        cost=Decimal("5.00"),
        stock_quantity=100,
    )
    await sale_service.record_quick_sale(
        actor=seller_user,
        product_id=prod.id,
        quantity=5,
    )

    metrics = await dash_service.get_dashboard_metrics("today")
    assert metrics["revenue"] == Decimal("75.00")
    assert metrics["cost"] == Decimal("25.00")
    assert metrics["gross_profit"] == Decimal("50.00")
    assert metrics["units_sold"] == 5


@pytest.mark.asyncio
async def test_ai_assistant_safe_queries(
    db_session: AsyncSession,
    admin_user: User,
    seller_user: User,
):
    ai_service = AIAssistantService(db_session)
    prod_service = ProductService(db_session)
    sale_service = SaleService(db_session)

    # Setup product
    prod = await prod_service.create_product(
        actor=admin_user,
        name="Vitamin C",
        sku="VIT-C",
        retail_price=Decimal("25.00"),
        cost=Decimal("10.00"),
        stock_quantity=3,
        minimum_stock=10,  # low stock!
    )
    await sale_service.record_quick_sale(
        actor=seller_user,
        product_id=prod.id,
        quantity=2,
    )

    # Test sales query
    response_sales = await ai_service.ask(user=seller_user, prompt="How much did we sell today?")
    assert "$50.00" in response_sales

    # Test low stock query
    response_stock = await ai_service.ask(user=seller_user, prompt="Show low stock products")
    assert "Vitamin C" in response_stock

    # Test reminder creation
    response_remind = await ai_service.ask(user=seller_user, prompt="Remind me to call the supplier")
    assert "call the supplier" in response_remind
