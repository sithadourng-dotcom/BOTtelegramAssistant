"""User repository for database operations."""

from typing import List, Optional, Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.user import User, UserRole, UserStatus


class UserRepository:
    """Repository handling User database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        clean = username.lstrip("@").strip()
        stmt = select(User).where(User.username.ilike(clean))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        telegram_id: int,
        full_name: str,
        username: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: UserRole = UserRole.VIEWER,
        status: UserStatus = UserStatus.PENDING,
        manager_id: Optional[int] = None,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username.lstrip("@") if username else None,
            phone_number=phone_number,
            role=role,
            status=status,
            manager_id=manager_id,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_status(self, user_id: int, status: UserStatus) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if user:
            user.status = status
            await self.session.flush()
        return user

    async def update_role(self, user_id: int, role: UserRole) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if user:
            user.role = role
            await self.session.flush()
        return user

    async def list_users(
        self,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        manager_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[User]:
        stmt = select(User)
        if role:
            stmt = stmt.where(User.role == role)
        if status:
            stmt = stmt.where(User.status == status)
        if manager_id:
            stmt = stmt.where(User.manager_id == manager_id)
        stmt = stmt.order_by(User.id.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pending_users(self) -> Sequence[User]:
        stmt = select(User).where(User.status == UserStatus.PENDING).order_by(User.created_at.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_team_members(self) -> Sequence[User]:
        stmt = select(User).where(User.status == UserStatus.APPROVED, User.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_active_sellers(self) -> int:
        stmt = select(User).where(
            User.role.in_([UserRole.SELLER, UserRole.LEADER, UserRole.MANAGER]),
            User.status == UserStatus.APPROVED,
            User.is_active == True,
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
