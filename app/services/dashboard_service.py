"""Dashboard statistics service (F-DB) — Member F"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_stats(self) -> dict:
        result = await self.db.execute(text(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status=1 THEN 1 ELSE 0 END) as active, "
            "SUM(CASE WHEN is_online=1 THEN 1 ELSE 0 END) as online "
            "FROM sys_user WHERE is_deleted=0"
        ))
        row = result.fetchone()
        return {"total": row[0] or 0, "active": row[1] or 0, "online": row[2] or 0}

    async def get_message_trend(self, days: int = 7) -> list:
        return []  # TODO: query im_message for daily counts

    async def get_crawler_stats(self) -> dict:
        result = await self.db.execute(text(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN is_enabled=1 THEN 1 ELSE 0 END) as enabled "
            "FROM crawler_task WHERE is_deleted=0"
        ))
        row = result.fetchone()
        return {"total_tasks": row[0] or 0, "enabled": row[1] or 0}
