"""Unit tests for global search and CSV/Excel exports."""

from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.user import User
from app.services.export import ExportService
from app.services.products import ProductService
from app.services.sales import SaleService
from app.services.search import SearchService


@pytest.mark.asyncio
async def test_global_search(db_session: AsyncSession, admin_user: User, seller_user: User):
    prod_service = ProductService(db_session)
    search_service = SearchService(db_session)

    await prod_service.create_product(
        actor=admin_user,
        name="Gold Collagen Mask",
        sku="MASK-GOLD",
        retail_price=Decimal("18.00"),
    )

    results = await search_service.search_all("collagen")
    assert len(results["products"]) == 1
    assert results["products"][0].name == "Gold Collagen Mask"


@pytest.mark.asyncio
async def test_csv_and_excel_export_generation(
    db_session: AsyncSession,
    admin_user: User,
    seller_user: User,
):
    prod_service = ProductService(db_session)
    sale_service = SaleService(db_session)
    export_service = ExportService(db_session)

    prod = await prod_service.create_product(
        actor=admin_user,
        name="Export Test Lotion",
        sku="EXP-01",
        retail_price=Decimal("25.00"),
        cost=Decimal("10.00"),
        stock_quantity=50,
    )
    await sale_service.record_quick_sale(actor=seller_user, product_id=prod.id, quantity=2)

    # 1. Test CSV export
    csv_path = await export_service.generate_csv_report("daily")
    assert csv_path.exists()
    assert csv_path.suffix == ".csv"
    assert csv_path.stat().st_size > 0

    # 2. Test Excel export
    excel_path = await export_service.generate_excel_report("monthly")
    assert excel_path.exists()
    assert excel_path.suffix == ".xlsx"
    assert excel_path.stat().st_size > 0

    # Cleanup exported test files
    try:
        csv_path.unlink()
        excel_path.unlink()
    except Exception:
        pass
