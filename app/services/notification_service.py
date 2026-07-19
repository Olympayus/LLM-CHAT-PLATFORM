"""通知中心业务逻辑服务（成员C）

提供通知的创建、查询、已读管理等业务逻辑。
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationRead


class NotificationService:
    """通知中心服务"""

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        type: str,
        title: str,
        content: str,
        link: Optional[str] = None,
        sender_id: Optional[int] = None,
        is_global: int = 0,
    ) -> Notification:
        """创建通知"""
        notification = Notification(
            type=type,
            title=title,
            content=content,
            link=link,
            sender_id=sender_id,
            is_global=is_global,
        )
        db.add(notification)
        await db.flush()
        await db.refresh(notification)
        return notification

    @staticmethod
    async def get_notifications(
        db: AsyncSession,
        user_id: int,
        type_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[dict], int]:
        """获取用户通知列表（含已读状态）"""
        # 查询条件：全局通知 或 发给该用户的通知
        condition = Notification.is_global == 1
        if type_filter:
            condition = and_(condition, Notification.type == type_filter)

        # 查询总数
        count_query = select(func.count(Notification.id)).where(condition)
        total = await db.scalar(count_query) or 0

        # 查询通知列表
        query = (
            select(Notification)
            .where(condition)
            .order_by(desc(Notification.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        notifications = list(result.scalars().all())

        # 批量查询已读状态
        if notifications:
            nids = [n.id for n in notifications]
            read_query = select(NotificationRead).where(
                NotificationRead.notification_id.in_(nids),
                NotificationRead.user_id == user_id,
            )
            read_result = await db.execute(read_query)
            read_ids = {r.notification_id for r in read_result.scalars().all()}

        # 组装返回数据
        items = []
        for n in notifications:
            items.append({
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "content": n.content,
                "link": n.link,
                "is_read": 1 if n.id in read_ids else 0,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            })

        return items, total

    @staticmethod
    async def get_notification_detail(
        db: AsyncSession,
        notification_id: int,
        user_id: int,
    ) -> Optional[dict]:
        """获取通知详情（同时标记已读）"""
        query = select(Notification).where(Notification.id == notification_id)
        result = await db.execute(query)
        notification = result.scalar_one_or_none()
        if not notification:
            return None

        # 自动标记已读
        await NotificationService.mark_read(db, notification_id, user_id)

        return {
            "id": notification.id,
            "type": notification.type,
            "title": notification.title,
            "content": notification.content,
            "link": notification.link,
            "sender_id": notification.sender_id,
            "is_global": notification.is_global,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        }

    @staticmethod
    async def mark_read(db: AsyncSession, notification_id: int, user_id: int) -> bool:
        """标记单条通知为已读"""
        # 检查是否已存在已读记录
        query = select(NotificationRead).where(
            NotificationRead.notification_id == notification_id,
            NotificationRead.user_id == user_id,
        )
        result = await db.execute(query)
        if result.scalar_one_or_none():
            return True  # 已标记过

        read_record = NotificationRead(
            notification_id=notification_id,
            user_id=user_id,
        )
        db.add(read_record)
        await db.flush()
        return True

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: int) -> int:
        """标记所有通知为已读，返回新标记的数量"""
        # 获取所有未读的全局通知
        query = select(Notification.id).where(Notification.is_global == 1)
        result = await db.execute(query)
        all_ids = [row[0] for row in result.all()]

        if not all_ids:
            return 0

        # 获取已读通知ID
        read_query = select(NotificationRead.notification_id).where(
            NotificationRead.notification_id.in_(all_ids),
            NotificationRead.user_id == user_id,
        )
        read_result = await db.execute(read_query)
        read_ids = {row[0] for row in read_result.all()}

        # 批量插入未读的已读记录
        count = 0
        for nid in all_ids:
            if nid not in read_ids:
                db.add(NotificationRead(notification_id=nid, user_id=user_id))
                count += 1

        await db.flush()
        return count

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: int) -> int:
        """获取用户未读通知数"""
        query = select(func.count(Notification.id)).where(Notification.is_global == 1)
        total = await db.scalar(query) or 0

        read_query = select(func.count(NotificationRead.id)).where(
            NotificationRead.user_id == user_id,
        )
        read_count = await db.scalar(read_query) or 0

        return max(0, total - read_count)


notification_service = NotificationService()