"""Global search service across business entities."""

from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.customer_repo import CustomerRepository
from app.database.repositories.order_repo import OrderRepository
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.task_repo import TaskRepository


class SearchService:
    """Service performing unified global search."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.order_repo = OrderRepository(session)
        self.user_repo = UserRepository(session)
        self.task_repo = TaskRepository(session)

    async def search_all(self, query: str, limit_per_entity: int = 5) -> Dict[str, List[Any]]:
        clean_q = query.strip()
        if not clean_q:
            return {"products": [], "customers": [], "orders": [], "users": [], "tasks": []}

        products = await self.product_repo.search_products(clean_q, limit=limit_per_entity)
        customers = await self.customer_repo.search_customers(clean_q, limit=limit_per_entity)

        # Orders search by order_number
        orders = []
        if clean_q.upper().startswith("ORD") or clean_q.isdigit():
            order = await self.order_repo.get_by_order_number(clean_q.upper())
            if order:
                orders.append(order)

        # Users search
        users = []
        user_by_name = await self.user_repo.get_by_username(clean_q)
        if user_by_name:
            users.append(user_by_name)

        # Tasks search
        tasks = await self.task_repo.list_tasks(limit=limit_per_entity)
        matching_tasks = [t for t in tasks if clean_q.lower() in t.title.lower()]

        return {
            "products": list(products),
            "customers": list(customers),
            "orders": orders,
            "users": users,
            "tasks": matching_tasks[:limit_per_entity],
        }
