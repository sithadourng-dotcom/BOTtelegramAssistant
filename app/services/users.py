"""User service for authentication, roles, registration, and approvals."""

from typing import List, Optional, Sequence, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database.models.user import User, UserRole, UserStatus
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.audit_repo import AuditRepository


ROLE_HIERARCHY = {
    UserRole.OWNER: 100,
    UserRole.ADMIN: 80,
    UserRole.MANAGER: 60,
    UserRole.LEADER: 40,
    UserRole.SELLER: 20,
    UserRole.PROMOTER: 20,
    UserRole.VIEWER: 10,
}


def has_permission(user: Optional[User], required_role: UserRole) -> bool:
    """Check if the user has at least the required role permission."""
    if not user:
        return False
    if user.status != UserStatus.APPROVED and user.role != UserRole.OWNER:
        return False
    # If the user is the owner telegram id, always grant
    if user.telegram_id == settings.ADMIN_TELEGRAM_ID or user.role == UserRole.OWNER:
        return True
    user_level = ROLE_HIERARCHY.get(user.role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


class UserService:
    """Business logic for User operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.audit_repo = AuditRepository(session)

    async def get_or_register_user(
        self,
        telegram_id: int,
        full_name: str,
        username: Optional[str] = None,
        phone_number: Optional[str] = None,
        requested_role: UserRole = UserRole.SELLER,
    ) -> Tuple[User, bool]:
        """
        Check if user exists; if not, create as pending or owner if configured.
        Returns: (user, is_new)
        """
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user:
            # Update username if changed
            if username and user.username != username.lstrip("@"):
                user.username = username.lstrip("@")
                await self.session.flush()
            return user, False

        # If this telegram_id matches the owner in settings, auto-approve as OWNER
        is_owner = (telegram_id == settings.ADMIN_TELEGRAM_ID)
        role = UserRole.OWNER if is_owner else requested_role
        status = UserStatus.APPROVED if is_owner else UserStatus.PENDING

        user = await self.user_repo.create_user(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            phone_number=phone_number,
            role=role,
            status=status,
        )

        await self.audit_repo.log_action(
            action="USER_REGISTERED",
            entity_type="User",
            user_id=user.id,
            entity_id=str(user.id),
            new_value=f"role={role.value}, status={status.value}",
        )
        return user, True

    async def approve_user(self, admin_user: User, user_id: int, assigned_role: Optional[UserRole] = None) -> Optional[User]:
        """Approve a pending user and optionally set role."""
        if not has_permission(admin_user, UserRole.ADMIN):
            raise PermissionError("Only Admin or Owner can approve users.")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        old_val = f"status={user.status.value}, role={user.role.value}"
        user.status = UserStatus.APPROVED
        if assigned_role:
            user.role = assigned_role
        await self.session.flush()

        await self.audit_repo.log_action(
            action="USER_APPROVED",
            entity_type="User",
            user_id=admin_user.id,
            entity_id=str(user.id),
            old_value=old_val,
            new_value=f"status={user.status.value}, role={user.role.value}",
        )
        return user

    async def reject_user(self, admin_user: User, user_id: int) -> Optional[User]:
        """Reject a pending user."""
        if not has_permission(admin_user, UserRole.ADMIN):
            raise PermissionError("Only Admin or Owner can reject users.")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        old_status = user.status.value
        user.status = UserStatus.REJECTED
        await self.session.flush()

        await self.audit_repo.log_action(
            action="USER_REJECTED",
            entity_type="User",
            user_id=admin_user.id,
            entity_id=str(user.id),
            old_value=f"status={old_status}",
            new_value="status=REJECTED",
        )
        return user

    async def assign_role(self, admin_user: User, user_id: int, new_role: UserRole) -> Optional[User]:
        """Change a user's role."""
        if not has_permission(admin_user, UserRole.ADMIN):
            raise PermissionError("Only Admin or Owner can assign roles.")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        old_role = user.role.value
        user.role = new_role
        await self.session.flush()

        await self.audit_repo.log_action(
            action="USER_ROLE_CHANGED",
            entity_type="User",
            user_id=admin_user.id,
            entity_id=str(user.id),
            old_value=f"role={old_role}",
            new_value=f"role={new_role.value}",
        )
        return user

    async def list_pending_users(self) -> Sequence[User]:
        return await self.user_repo.get_pending_users()

    async def list_team_members(self) -> Sequence[User]:
        return await self.user_repo.get_active_team_members()
