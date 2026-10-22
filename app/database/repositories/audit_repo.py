"""Audit log repository for tracking changes."""

from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.audit_log import AuditLog
from app.utils.tz import now_tz


class AuditRepository:
    """Repository handling system audit trail."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_action(
        self,
        action: str,
        entity_type: str,
        user_id: Optional[int] = None,
        entity_id: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action.strip(),
            entity_type=entity_type.strip(),
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            timestamp=now_tz(),
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_logs(
        self,
        entity_type: Optional[str] = None,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        stmt = select(AuditLog)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()
