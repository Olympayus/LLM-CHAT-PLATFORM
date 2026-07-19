"""System config service (F-SC) — Member F"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.sys_config import SysConfig


class SysConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[SysConfig]:
        result = await self.db.execute(select(SysConfig).order_by(SysConfig.category, SysConfig.config_key))
        return result.scalars().all()

    async def get_by_category(self, category: str) -> list[SysConfig]:
        result = await self.db.execute(select(SysConfig).where(SysConfig.category == category))
        return result.scalars().all()

    async def upsert(self, config_key: str, config_value: str, category: str,
                     description: Optional[str] = None) -> SysConfig:
        result = await self.db.execute(select(SysConfig).where(SysConfig.config_key == config_key))
        existing = result.scalar_one_or_none()
        if existing:
            existing.config_value = config_value
            existing.description = description
        else:
            existing = SysConfig(config_key=config_key, config_value=config_value, category=category, description=description)
            self.db.add(existing)
        await self.db.flush()
        return existing

    async def get_site_info(self) -> dict:
        site_configs = await self.get_by_category("site")
        info = {}
        for c in site_configs:
            info[c.config_key] = c.config_value
        return {"site_name": info.get("site_name", "LLM Platform"), "logo_url": info.get("logo_url"), "icp_number": info.get("icp_number")}
