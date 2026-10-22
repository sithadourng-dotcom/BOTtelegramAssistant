import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.database.database import get_db_context, init_db
from app.database.models.user import User, UserRole, UserStatus
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.customer_repo import CustomerRepository
from app.database.repositories.sale_repo import SaleRepository
from app.database.repositories.task_repo import TaskRepository
from app.database.repositories.activity_repo import ActivityRepository
from app.database.repositories.report_repo import ReportRepository
from app.database.models.task import TaskPriority
from app.utils.tz import today_tz


async def seed() -> None:
    print("Initializing database...")
    await init_db()

    async with get_db_context() as session:
        user_repo = UserRepository(session)
        prod_repo = ProductRepository(session)
        cust_repo = CustomerRepository(session)
        sale_repo = SaleRepository(session)
        task_repo = TaskRepository(session)
        act_repo = ActivityRepository(session)
        rep_repo = ReportRepository(session)

        # 1. Create Demo Seller & Manager
        manager = await user_repo.get_by_telegram_id(100001)
        if not manager:
            manager = await user_repo.create_user(
                telegram_id=100001,
                full_name="Sarah Miller (Manager)",
                username="sarah_manager",
                role=UserRole.MANAGER,
                status=UserStatus.APPROVED,
            )

        seller = await user_repo.get_by_telegram_id(100002)
        if not seller:
            seller = await user_repo.create_user(
                telegram_id=100002,
                full_name="John David (Seller)",
                username="john_seller",
                role=UserRole.SELLER,
                status=UserStatus.APPROVED,
            )

        # 2. Create Demo Products
        products_data = [
            ("Whitening Body Lotion 250ml", "LOTION-250", "Skincare", Decimal("25.00"), Decimal("18.00"), Decimal("9.50"), 85, 15),
            ("Hydrating Face Serum 50ml", "SERUM-50", "Skincare", Decimal("35.00"), Decimal("24.00"), Decimal("12.00"), 42, 10),
            ("Collagen Peptide Glow Drink", "GLOW-DRINK", "Supplements", Decimal("45.00"), Decimal("32.00"), Decimal("18.00"), 120, 20),
            ("UV Defense Sunscreen SPF50+", "SUN-SPF50", "Sun Protection", Decimal("18.50"), Decimal("13.00"), Decimal("6.50"), 8, 15),  # Low stock
            ("Exfoliating Coffee Body Scrub", "SCRUB-200", "Body Care", Decimal("15.00"), Decimal("10.50"), Decimal("5.00"), 65, 10),
        ]

        products = []
        for name, sku, cat, retail, wholesale, cost, stock, min_stock in products_data:
            existing = await prod_repo.get_by_sku(sku)
            if not existing:
                p = await prod_repo.create_product(
                    name=name,
                    sku=sku,
                    category=cat,
                    retail_price=retail,
                    wholesale_price=wholesale,
                    cost=cost,
                    stock_quantity=stock,
                    minimum_stock=min_stock,
                )
                products.append(p)
            else:
                products.append(existing)

        # 3. Create Demo Customers
        customers_data = [
            ("Chanthy Sok", "+85512998877", "chanthy_s"),
            ("Bopha Keo", "+85598112233", "bopha_k"),
            ("Vicheka Pich", "+85577665544", "vicheka_p"),
        ]
        customers = []
        for cname, cphone, cuser in customers_data:
            existing = await cust_repo.get_by_phone(cphone)
            if not existing:
                c = await cust_repo.create_customer(name=cname, phone=cphone, telegram_username=cuser, seller_id=seller.id)
                customers.append(c)
            else:
                customers.append(existing)

        # 4. Create Sample Sales for Today and Yesterday
        today = today_tz()
        yesterday = today - timedelta(days=1)

        # Today's sales
        await sale_repo.record_sale(
            seller_id=seller.id,
            product_id=products[0].id,
            quantity=3,
            unit_price=products[0].retail_price,
            cost_price=products[0].cost,
            sale_date=today,
            customer_id=customers[0].id,
            notes="Direct retail sale",
        )
        await sale_repo.record_sale(
            seller_id=seller.id,
            product_id=products[1].id,
            quantity=2,
            unit_price=products[1].retail_price,
            cost_price=products[1].cost,
            sale_date=today,
            customer_id=customers[1].id,
            notes="Followup purchase",
        )

        # 5. Create Sample Tasks
        await task_repo.create_task(
            title="Follow up with wholesale distributor in Siem Reap",
            description="Discuss special 50-unit price for Serum",
            created_by=manager.id,
            assigned_to=seller.id,
            priority=TaskPriority.HIGH,
        )
        await task_repo.create_task(
            title="Restock UV Defense Sunscreen inventory",
            description="Stock is down to 8 units. Minimum is 15.",
            created_by=manager.id,
            assigned_to=manager.id,
            priority=TaskPriority.HIGH,
        )

        # 6. Sample Daily Report
        await rep_repo.submit_or_update(
            user_id=seller.id,
            report_date=yesterday,
            sales_amount=Decimal("145.00"),
            orders_count=5,
            new_customers_count=2,
            videos_posted=3,
            messages_answered=24,
            followups_count=8,
            problems_faced="Customers asked for smaller travel size bottle",
            tomorrow_goal="Close 2 more wholesale leads",
        )

        # 7. Sample Activities
        await act_repo.log_activity(user_id=seller.id, activity_type="tiktok_video", quantity=2, activity_date=today)
        await act_repo.log_activity(user_id=seller.id, activity_type="facebook_post", quantity=3, activity_date=today)

        print("✅ Demo data seeded successfully!")
        print(f"Created {len(products)} products, {len(customers)} customers, sample sales, activities, and tasks.")


if __name__ == "__main__":
    asyncio.run(seed())
