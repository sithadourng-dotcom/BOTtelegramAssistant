"""Pytest configuration and async test fixtures."""

import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models.base import Base
from app.database.models.user import User, UserRole, UserStatus
from app.services.users import UserService

# Isolated test database in memory
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh in-memory database session for each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def owner_user(db_session: AsyncSession) -> User:
    """Fixture providing an approved Owner user."""
    user = User(
        telegram_id=999001,
        full_name="Alice Owner",
        username="alice_owner",
        phone_number="+85512000001",
        role=UserRole.OWNER,
        status=UserStatus.APPROVED,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Fixture providing an approved Admin user."""
    user = User(
        telegram_id=999002,
        full_name="Bob Admin",
        username="bob_admin",
        phone_number="+85512000002",
        role=UserRole.ADMIN,
        status=UserStatus.APPROVED,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def seller_user(db_session: AsyncSession) -> User:
    """Fixture providing an approved Seller user."""
    user = User(
        telegram_id=999003,
        full_name="Charlie Seller",
        username="charlie_seller",
        phone_number="+85512000003",
        role=UserRole.SELLER,
        status=UserStatus.APPROVED,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Fixture providing an approved Viewer user."""
    user = User(
        telegram_id=999004,
        full_name="Dave Viewer",
        username="dave_viewer",
        phone_number="+85512000004",
        role=UserRole.VIEWER,
        status=UserStatus.APPROVED,
    )
    db_session.add(user)
    await db_session.flush()
    return user
