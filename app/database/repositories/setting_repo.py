"""Setting repository for dynamic business settings."""

from typing import Dict, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.setting import SystemSetting
from app.utils.tz import now_tz


class SettingRepository:
    """Repository handling dynamic key-value system settings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        stmt = select(SystemSetting.value).where(SystemSetting.key == key)
        result = await self.session.execute(stmt)
        val = result.scalar_one_or_none()
        return val if val is not None else default

    async def set_value(self, key: str, value: str, description: Optional[str] = None) -> SystemSetting:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.session.execute(stmt)
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
            if description:
                setting.description = description
            setting.updated_at = now_tz()
        else:
            setting = SystemSetting(
                key=key,
                value=value,
                description=description,
                updated_at=now_tz(),
            )
            self.session.add(setting)
        await self.session.flush()
        return setting

    async def get_all_settings(self) -> Dict[str, str]:
        stmt = select(SystemSetting)
        result = await self.session.execute(stmt)
        settings = result.scalars().all()
        return {s.key: s.value for s in settings}
