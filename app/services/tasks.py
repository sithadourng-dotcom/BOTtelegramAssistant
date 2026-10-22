"""Task management service."""

from datetime import datetime
from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.task import Task, TaskPriority, TaskStatus
from app.database.models.user import User, UserRole
from app.database.repositories.task_repo import TaskRepository
from app.database.repositories.audit_repo import AuditRepository
from app.services.users import has_permission


class TaskService:
    """Service handling task assignment, status updates, and deadlines."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_repo = TaskRepository(session)
        self.audit_repo = AuditRepository(session)

    async def create_task(
        self,
        creator: User,
        title: str,
        description: Optional[str] = None,
        assigned_to: Optional[int] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: Optional[datetime] = None,
    ) -> Task:
        if not has_permission(creator, UserRole.SELLER):
            raise PermissionError("Permission denied.")

        task = await self.task_repo.create_task(
            title=title,
            created_by=creator.id,
            description=description,
            assigned_to=assigned_to or creator.id,
            priority=priority,
            due_date=due_date,
        )

        await self.audit_repo.log_action(
            action="TASK_CREATED",
            entity_type="Task",
            user_id=creator.id,
            entity_id=str(task.id),
            new_value=f"title={task.title}, priority={task.priority.value}, assigned_to={task.assigned_to}",
        )
        return task

    async def update_task_status(self, actor: User, task_id: int, status: TaskStatus) -> Optional[Task]:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return None

        # Users can update tasks assigned to them or if they are admin/manager
        if task.assigned_to != actor.id and not has_permission(actor, UserRole.MANAGER):
            raise PermissionError("Permission denied: You can only update tasks assigned to you.")

        old_status = task.status.value
        task.status = status
        await self.session.flush()

        await self.audit_repo.log_action(
            action="TASK_STATUS_UPDATED",
            entity_type="Task",
            user_id=actor.id,
            entity_id=str(task.id),
            old_value=f"status={old_status}",
            new_value=f"status={status.value}",
        )
        return task

    async def get_task(self, task_id: int) -> Optional[Task]:
        return await self.task_repo.get_by_id(task_id)

    async def list_tasks(
        self,
        assigned_to: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
    ) -> Sequence[Task]:
        return await self.task_repo.list_tasks(assigned_to=assigned_to, status=status, priority=priority)

    async def get_overdue_tasks(self) -> Sequence[Task]:
        return await self.task_repo.get_overdue_tasks()
