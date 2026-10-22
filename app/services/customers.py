"""Customer CRM service for tracking customer profiles and purchase history."""

from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.customer import Customer
from app.database.models.user import User, UserRole
from app.database.repositories.customer_repo import CustomerRepository
from app.database.repositories.audit_repo import AuditRepository
from app.services.users import has_permission


class CustomerService:
    """Service handling Customer CRM operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.customer_repo = CustomerRepository(session)
        self.audit_repo = AuditRepository(session)

    async def get_or_create_customer(
        self,
        actor: User,
        name: str,
        phone: str,
        telegram_username: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Customer:
        if not has_permission(actor, UserRole.SELLER):
            raise PermissionError("Permission denied.")

        clean_phone = phone.strip()
        existing = await self.customer_repo.get_by_phone(clean_phone)
        if existing:
            if telegram_username and not existing.telegram_username:
                existing.telegram_username = telegram_username.lstrip("@")
            if notes and not existing.notes:
                existing.notes = notes
            await self.session.flush()
            return existing

        customer = await self.customer_repo.create_customer(
            name=name,
            phone=clean_phone,
            telegram_username=telegram_username,
            seller_id=actor.id,
            notes=notes,
        )

        await self.audit_repo.log_action(
            action="CUSTOMER_CREATED",
            entity_type="Customer",
            user_id=actor.id,
            entity_id=str(customer.id),
            new_value=f"name={customer.name}, phone={customer.phone}",
        )
        return customer

    async def get_customer(self, customer_id: int) -> Optional[Customer]:
        return await self.customer_repo.get_by_id(customer_id)

    async def search_customers(self, query: str) -> Sequence[Customer]:
        return await self.customer_repo.search_customers(query)

    async def list_customers(self, seller_id: Optional[int] = None) -> Sequence[Customer]:
        return await self.customer_repo.list_customers(seller_id=seller_id)
