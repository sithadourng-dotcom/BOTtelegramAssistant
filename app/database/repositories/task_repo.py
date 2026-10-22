"""Task repository for task assignment and lifecycle operations."""

from datetime import datetime
from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.task import Task, TaskPriority, TaskStatus
from app.utils.tz import now_tz


class TaskRepository:
    """Repository handling Task delegation and tracking."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, task_id: int) -> Optional[Task]:
        stmt = select(Task).where(Task.id == task_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_task(
        self,
        title: str,
        created_by: int,
        description: Optional[str] = None,
        assigned_to: Optional[int] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: Optional[datetime] = None,
    ) -> Task:
        task = Task(
            title=title.strip(),
            created_by=created_by,
            description=description,
            assigned_to=assigned_to,
            priority=priority,
            due_date=due_date,
            status=TaskStatus.TODO,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def update_status(self, task_id: int, status: TaskStatus) -> Optional[Task]:
        task = await self.get_by_id(task_id)
        if task:
            task.status = status
            await self.session.flush()
        return task

    async def list_tasks(
        self,
        assigned_to: Optional[int] = None,
        created_by: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Task]:
        stmt = select(Task)
        if assigned_to:
            stmt = stmt.where(Task.assigned_to == assigned_to)
        if created_by:
            stmt = stmt.where(Task.created_by == created_by)
        if status:
            stmt = stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        stmt = stmt.order_by(Task.due_date.asc().nulls_last(), Task.id.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_overdue_tasks(self) -> Sequence[Task]:
        current_time = now_tz()
        stmt = select(Task).where(
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
            Task.due_date != None,
            Task.due_date < current_time,
        ).order_by(Task.due_date.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_open_tasks(self, user_id: Optional[int] = None) -> int:
        stmt = select(func.count(Task.id)).where(Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]))
        if user_id:
            stmt = stmt.where(Task.assigned_to == user_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
