"""Customer repository for CRM database operations."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.customer import Customer


class CustomerRepository:
    """Repository handling Customer CRM operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, customer_id: int) -> Optional[Customer]:
        stmt = select(Customer).where(Customer.id == customer_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[Customer]:
        clean = phone.strip()
        stmt = select(Customer).where(Customer.phone == clean)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_customer(
        self,
        name: str,
        phone: str,
        telegram_username: Optional[str] = None,
        seller_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Customer:
        customer = Customer(
            name=name.strip(),
            phone=phone.strip(),
            telegram_username=telegram_username.lstrip("@") if telegram_username else None,
            seller_id=seller_id,
            notes=notes,
            total_orders=0,
            total_spent=Decimal("0.00"),
        )
        self.session.add(customer)
        await self.session.flush()
        return customer

    async def get_or_create(
        self,
        name: str,
        phone: str,
        telegram_username: Optional[str] = None,
        seller_id: Optional[int] = None,
    ) -> Customer:
        existing = await self.get_by_phone(phone)
        if existing:
            if not existing.telegram_username and telegram_username:
                existing.telegram_username = telegram_username.lstrip("@")
                await self.session.flush()
            return existing
        return await self.create_customer(
            name=name,
            phone=phone,
            telegram_username=telegram_username,
            seller_id=seller_id,
        )

    async def search_customers(self, query: str, limit: int = 20) -> Sequence[Customer]:
        pattern = f"%{query.strip()}%"
        stmt = select(Customer).where(
            or_(
                Customer.name.ilike(pattern),
                Customer.phone.ilike(pattern),
                Customer.telegram_username.ilike(pattern),
            )
        ).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_customers(
        self,
        seller_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Customer]:
        stmt = select(Customer)
        if seller_id:
            stmt = stmt.where(Customer.seller_id == seller_id)
        stmt = stmt.order_by(Customer.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_stats(self, customer_id: int, order_amount: Decimal, order_time: datetime) -> Optional[Customer]:
        customer = await self.get_by_id(customer_id)
        if customer:
            customer.total_orders += 1
            customer.total_spent += order_amount
            customer.last_order_date = order_time
            await self.session.flush()
        return customer

    async def count_repeat_customers(self) -> int:
        stmt = select(Customer).where(Customer.total_orders >= 2)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
