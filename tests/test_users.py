"""Unit tests for user registration, approvals, and role permissions."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.user import User, UserRole, UserStatus
from app.services.users import UserService, has_permission


@pytest.mark.asyncio
async def test_user_registration_creates_pending(db_session: AsyncSession):
    user_service = UserService(db_session)
    user, is_new = await user_service.get_or_register_user(
        telegram_id=12345678,
        full_name="John Doe",
        username="johndoe",
        phone_number="+85511223344",
        requested_role=UserRole.SELLER,
    )
    assert is_new is True
    assert user.telegram_id == 12345678
    assert user.full_name == "John Doe"
    assert user.status == UserStatus.PENDING
    assert user.role == UserRole.SELLER


@pytest.mark.asyncio
async def test_admin_approves_and_assigns_role(db_session: AsyncSession, admin_user: User):
    user_service = UserService(db_session)
    pending_user, _ = await user_service.get_or_register_user(
        telegram_id=87654321,
        full_name="Jane Seller",
        username="janeseller",
    )
    assert pending_user.status == UserStatus.PENDING

    # Admin approves and assigns MANAGER
    approved = await user_service.approve_user(
        admin_user=admin_user,
        user_id=pending_user.id,
        assigned_role=UserRole.MANAGER,
    )
    assert approved is not None
    assert approved.status == UserStatus.APPROVED
    assert approved.role == UserRole.MANAGER


@pytest.mark.asyncio
async def test_non_admin_cannot_approve(db_session: AsyncSession, seller_user: User):
    user_service = UserService(db_session)
    pending_user, _ = await user_service.get_or_register_user(
        telegram_id=55566677,
        full_name="Sam Prom",
    )

    with pytest.raises(PermissionError):
        await user_service.approve_user(admin_user=seller_user, user_id=pending_user.id)


@pytest.mark.asyncio
async def test_role_hierarchy_permissions(owner_user: User, admin_user: User, seller_user: User, viewer_user: User):
    # Owner has access to everything
    assert has_permission(owner_user, UserRole.OWNER) is True
    assert has_permission(owner_user, UserRole.ADMIN) is True
    assert has_permission(owner_user, UserRole.SELLER) is True

    # Admin has access to Seller, but not Owner
    assert has_permission(admin_user, UserRole.OWNER) is False
    assert has_permission(admin_user, UserRole.ADMIN) is True
    assert has_permission(admin_user, UserRole.SELLER) is True

    # Seller has access to Seller & Viewer, but not Admin
    assert has_permission(seller_user, UserRole.ADMIN) is False
    assert has_permission(seller_user, UserRole.SELLER) is True
    assert has_permission(seller_user, UserRole.VIEWER) is True

    # Viewer cannot perform Seller actions
    assert has_permission(viewer_user, UserRole.SELLER) is False
    assert has_permission(viewer_user, UserRole.VIEWER) is True
