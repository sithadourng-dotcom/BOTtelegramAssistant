"""Task management model and enums."""

import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base, TimestampMixin


class TaskPriority(str, enum.Enum):
    """Priority level for business tasks."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def get_badge(cls, priority: "TaskPriority") -> str:
        badges = {
            cls.HIGH: "🔴 High",
            cls.MEDIUM: "🟡 Medium",
            cls.LOW: "🟢 Low",
        }
        return badges.get(priority, priority.value)


class TaskStatus(str, enum.Enum):
    """Execution status for business tasks."""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    @classmethod
    def get_badge(cls, status: "TaskStatus") -> str:
        badges = {
            cls.TODO: "📝 To Do",
            cls.IN_PROGRESS: "🔄 In Progress",
            cls.COMPLETED: "✅ Completed",
            cls.CANCELLED: "❌ Cancelled",
        }
        return badges.get(status, status.value)


class Task(Base, TimestampMixin):
    """Business task delegation and tracking."""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority_enum", native_enum=False),
        default=TaskPriority.MEDIUM,
        nullable=False,
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status_enum", native_enum=False),
        default=TaskStatus.TODO,
        nullable=False,
        index=True,
    )

    # Relationships
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to], lazy="joined")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], lazy="joined")

    def __repr__(self) -> str:
        return f"<Task id={self.id} title='{self.title}' status={self.status} priority={self.priority}>"
