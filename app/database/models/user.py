"""User model and role/status enums."""

import enum
from typing import Optional, List
from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """Business user roles with hierarchical permissions."""
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    LEADER = "LEADER"
    SELLER = "SELLER"
    PROMOTER = "PROMOTER"
    VIEWER = "VIEWER"

    @classmethod
    def get_display_name(cls, role: "UserRole") -> str:
        icons = {
            cls.OWNER: "👑 Owner",
            cls.ADMIN: "🛡️ Admin",
            cls.MANAGER: "👔 Manager",
            cls.LEADER: "⭐ Leader",
            cls.SELLER: "💼 Seller",
            cls.PROMOTER: "📣 Promoter",
            cls.VIEWER: "👀 Viewer",
        }
        return icons.get(role, role.value)


class UserStatus(str, enum.Enum):
    """User account lifecycle status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class User(Base, TimestampMixin):
    """User account model."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", native_enum=False),
        default=UserRole.VIEWER,
        nullable=False,
        index=True,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status_enum", native_enum=False),
        default=UserStatus.PENDING,
        nullable=False,
        index=True,
    )
    manager_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    manager: Mapped[Optional["User"]] = relationship("User", remote_side=[id], backref="subordinates")

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id} name='{self.full_name}' role={self.role}>"
