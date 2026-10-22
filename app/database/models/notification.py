"""Notification and announcement models."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    """System notification or announcement record."""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    target_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    target_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(64), default="ANNOUNCEMENT", nullable=False, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    sender: Mapped[Optional["User"]] = relationship("User", foreign_keys=[sender_id], lazy="joined")
    target_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[target_user_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type='{self.notification_type}' title='{self.title}'>"
