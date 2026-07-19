"""合规审计服务层

包含:
- 敏感词管理（CRUD + DFA 刷新）
- 消息管理（搜索、撤回、导出）
- 群组管控（列表、禁言、解散、系统消息）
- 用户处置（禁言、封号）
- 审计日志（写入、查询）
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.im import ImSensitiveWord, ImGroup, ImGroupMember, ImMessage
from app.models.audit_log import SysAuditLog
from app.schemas.im import (
    SensitiveWordCreate,
    SensitiveWordUpdate,
    AuditLogSearchRequest,
    MessageSearchRequest,
    PageResult,
)
from app.utils.sensitive_filter import sensitive_filter
from app.services.elasticsearch_service import es_service


class ComplianceService:
    """合规审计服务"""

    # ==================== 敏感词管理 ====================

    async def get_words(
        self, db: AsyncSession, page: int = 1, page_size: int = 20
    ) -> PageResult:
        """获取敏感词列表"""
        # 查询总数
        count_query = select(func.count()).select_from(ImSensitiveWord)
        total = (await db.execute(count_query)).scalar() or 0

        # 分页查询
        query = (
            select(ImSensitiveWord)
            .order_by(ImSensitiveWord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        items = result.scalars().all()

        return PageResult(
            items=[item for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def create_word(self, db: AsyncSession, data: SensitiveWordCreate, created_by: int) -> ImSensitiveWord:
        """创建敏感词"""
        word = ImSensitiveWord(
            word=data.word,
            level=data.level,
            category=data.category,
            is_enabled=True,
            created_by=created_by,
        )
        db.add(word)
        await db.flush()
        await db.refresh(word)

        # 刷新 DFA 过滤器
        await self._reload_filter(db)

        return word

    async def update_word(self, db: AsyncSession, word_id: int, data: SensitiveWordUpdate) -> Optional[ImSensitiveWord]:
        """更新敏感词"""
        result = await db.execute(select(ImSensitiveWord).where(ImSensitiveWord.id == word_id))
        word = result.scalar_one_or_none()
        if not word:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            for key, value in update_data.items():
                setattr(word, key, value)
            word.updated_at = datetime.now()
            await db.flush()
            await db.refresh(word)

            # 刷新 DFA 过滤器
            await self._reload_filter(db)

        return word

    async def delete_word(self, db: AsyncSession, word_id: int) -> bool:
        """删除敏感词"""
        result = await db.execute(
            delete(ImSensitiveWord).where(ImSensitiveWord.id == word_id)
        )
        if result.rowcount == 0:
            return False

        # 刷新 DFA 过滤器
        await self._reload_filter(db)
        return True

    async def _reload_filter(self, db: AsyncSession) -> None:
        """从数据库重新加载所有启用的敏感词到 DFA 过滤器"""
        result = await db.execute(
            select(ImSensitiveWord).where(ImSensitiveWord.is_enabled == 1)
        )
        words = result.scalars().all()
        word_list = [
            {"word": w.word, "level": w.level}
            for w in words
        ]
        sensitive_filter.reload(word_list)

    # ==================== 消息管理 ====================

    async def search_messages(self, query: MessageSearchRequest) -> PageResult:
        """搜索消息（走 ES）"""
        result = await es_service.search_messages(query)
        return PageResult(
            items=result["items"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
        )

    async def recall_message(
        self,
        db: AsyncSession,
        message_id: int,
        admin_id: int,
        reason: str = "违规内容",
        ws_manager=None,
    ) -> bool:
        """强制撤回消息
        
        Args:
            db: 数据库会话
            message_id: 消息ID
            admin_id: 管理员ID
            reason: 撤回原因
            ws_manager: WebSocket 连接管理器（由成员C提供）
        """
        # 1. 查询消息
        result = await db.execute(select(ImMessage).where(ImMessage.id == message_id))
        message = result.scalar_one_or_none()
        if not message:
            return False

        # 2. 标记撤回
        message.is_recalled = 1
        message.recall_reason = reason
        message.recalled_by = admin_id
        await db.flush()

        # 3. 删除 ES 索引
        await es_service.delete_by_message_id(message_id)

        # 4. 写审计日志
        await self.write_log(
            db=db,
            user_id=admin_id,
            action="recall",
            resource="message",
            resource_id=message_id,
            detail={"reason": reason, "group_id": message.group_id, "sender_id": message.sender_id},
        )

        # 5. WS 广播撤回事件（配合成员C）
        if ws_manager and hasattr(ws_manager, "broadcast_recall"):
            await ws_manager.broadcast_recall(message.group_id, message_id, reason)

        return True

    async def export_messages(
        self, query: MessageSearchRequest, export_format: str = "excel"
    ) -> bytes:
        """导出聊天记录（PDF / Excel / CSV）

        通过 app/utils/export.py 中的 export_data 工具实现数据导出。

        Args:
            query: 消息搜索请求
            export_format: 导出格式，pdf 或 excel

        Returns:
            导出的文件内容（字节）
        """
        result = await self.search_messages(query)
        raw_items = result["items"]

        # 将 ORM 对象转为字典列表
        data = []
        for item in raw_items:
            if isinstance(item, dict):
                data.append(item)
            elif hasattr(item, "__dict__"):
                row = {
                    k: str(v) if not isinstance(v, (int, float, bool, type(None))) else v
                    for k, v in item.__dict__.items()
                    if not k.startswith("_")
                }
                data.append(row)
            else:
                data.append(str(item))

        from app.utils.export import export_data
        return await export_data(data, export_format=export_format)

    # ==================== 群组管控 ====================

    async def get_all_groups(
        self, db: AsyncSession, keyword: Optional[str] = None, page: int = 1, page_size: int = 20
    ) -> PageResult:
        """获取全平台群组列表"""
        query = select(ImGroup).where(ImGroup.is_deleted == 0)

        if keyword:
            query = query.where(ImGroup.group_name.like(f"%{keyword}%"))

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        # 分页
        query = query.order_by(ImGroup.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        groups = result.scalars().all()

        return PageResult(
            items=[group for group in groups],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_group_detail(self, db: AsyncSession, group_id: int) -> Optional[dict]:
        """获取群组详情 + 成员列表"""
        result = await db.execute(
            select(ImGroup).where(ImGroup.id == group_id, ImGroup.is_deleted == 0)
        )
        group = result.scalar_one_or_none()
        if not group:
            return None

        # 获取成员列表
        member_result = await db.execute(
            select(ImGroupMember).where(ImGroupMember.group_id == group_id)
        )
        members = member_result.scalars().all()

        return {
            "id": group.id,
            "group_name": group.group_name,
            "avatar_url": group.avatar_url,
            "owner_id": group.owner_id,
            "notice": group.notice,
            "member_count": group.member_count,
            "max_members": group.max_members,
            "is_bot_enabled": bool(group.is_bot_enabled),
            "is_muted_all": bool(group.is_muted_all),
            "status": group.status,
            "created_at": group.created_at,
            "members": [
                {
                    "id": m.id,
                    "user_type": m.user_type,
                    "user_id": m.user_id,
                    "role": m.role,
                    "joined_at": m.joined_at,
                }
                for m in members
            ],
        }

    async def remove_member(self, db: AsyncSession, group_id: int, member_id: int, admin_id: int) -> bool:
        """强制移除群成员"""
        result = await db.execute(
            delete(ImGroupMember).where(
                ImGroupMember.group_id == group_id,
                ImGroupMember.id == member_id,
            )
        )
        if result.rowcount == 0:
            return False

        # 更新成员计数
        await db.execute(
            update(ImGroup)
            .where(ImGroup.id == group_id)
            .values(member_count=ImGroup.member_count - 1)
        )

        # 写审计日志
        await self.write_log(
            db=db, user_id=admin_id, action="remove_member",
            resource="group", resource_id=group_id,
            detail={"member_id": member_id},
        )
        return True

    async def mute_all(self, db: AsyncSession, group_id: int, is_muted: bool, admin_id: int) -> bool:
        """全员禁言开关"""
        result = await db.execute(
            update(ImGroup)
            .where(ImGroup.id == group_id)
            .values(is_muted_all=1 if is_muted else 0)
        )
        if result.rowcount == 0:
            return False

        await self.write_log(
            db=db, user_id=admin_id, action="mute_all" if is_muted else "unmute_all",
            resource="group", resource_id=group_id,
        )
        return True

    async def toggle_bot(self, db: AsyncSession, group_id: int, enabled: bool, admin_id: int) -> bool:
        """开关数字员工应答"""
        result = await db.execute(
            update(ImGroup)
            .where(ImGroup.id == group_id)
            .values(is_bot_enabled=1 if enabled else 0)
        )
        if result.rowcount == 0:
            return False

        await self.write_log(
            db=db, user_id=admin_id, action="toggle_bot",
            resource="group", resource_id=group_id,
            detail={"enabled": enabled},
        )
        return True

    async def dismiss_group(self, db: AsyncSession, group_id: int, admin_id: int) -> bool:
        """解散群（软删除）"""
        result = await db.execute(
            update(ImGroup)
            .where(ImGroup.id == group_id)
            .values(status=0, is_deleted=1)
        )
        if result.rowcount == 0:
            return False

        await self.write_log(
            db=db, user_id=admin_id, action="dismiss",
            resource="group", resource_id=group_id,
        )
        return True

    async def send_system_message(
        self, db: AsyncSession, group_id: int, content: str, admin_id: int, ws_manager=None
    ) -> bool:
        """发送群系统消息"""
        # 创建系统消息记录
        message = ImMessage(
            chat_type="group",
            sender_type="system",
            sender_id=admin_id,
            group_id=group_id,
            msg_type="system",
            content=content,
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)

        # 写审计日志
        await self.write_log(
            db=db, user_id=admin_id, action="system_msg",
            resource="group", resource_id=group_id,
            detail={"content": content, "message_id": message.id},
        )

        # WS 广播系统消息（配合成员C）
        if ws_manager and hasattr(ws_manager, "send_group"):
            await ws_manager.send_group(
                group_id=group_id,
                message={
                    "type": "system_message",
                    "data": {
                        "message_id": message.id,
                        "content": content,
                    },
                },
            )

        return True

    # ==================== 用户处置 ====================

    async def mute_user(self, db: AsyncSession, user_id: int, duration_minutes: int, admin_id: int) -> bool:
        """禁言用户

        将禁言信息存储在 Redis 中（有自动过期时间），同时记录审计日志。
        
        Args:
            db: 数据库会话
            user_id: 被禁言用户ID
            duration_minutes: 禁言时长（分钟）
            admin_id: 操作管理员ID

        NOTE: 实际禁言判断需要成员C在 WS message_handler 中配合：
            1. 发送消息前检查 redis.exists(f"mute:{user_id}")
            2. 如果存在则拒绝发送
        """
        # 尝试写入 Redis（需要成员F提供 get_redis()）
        try:
            from app.core.redis import get_redis
            redis = await get_redis()
            await redis.setex(f"mute:{user_id}", duration_minutes * 60, "1")
        except (ImportError, Exception) as e:
            logging.warning(f"Redis 禁言存储失败（不影响日志记录）: {e}")

        # 记录审计日志
        await self.write_log(
            db=db, user_id=admin_id, action="mute",
            resource="user", resource_id=user_id,
            detail={"duration_minutes": duration_minutes},
        )
        return True

    async def ban_user(self, db: AsyncSession, user_id: int, reason: str, admin_id: int) -> bool:
        """封号

        将用户状态更新为 2（封号），同时记录审计日志。

        Args:
            db: 数据库会话
            user_id: 被封号用户ID
            reason: 封号原因
            admin_id: 操作管理员ID

        NOTE: 依赖成员A 的 SysUser 模型，当前使用 SQL 直接更新。
        成员A 接入 JWT 后应配合提供 ban/unban 专用接口。
        """
        # 尝试直接更新 SysUser 状态为 2（封号）
        # [F-01] 依赖成员A 的 SysUser 模型
        try:
            from sqlalchemy import update as sa_update
            from app.models.user import SysUser
            stmt = sa_update(SysUser).where(SysUser.id == user_id).values(status=2)
            result = await db.execute(stmt)
            if result.rowcount == 0:
                logging.warning(f"封号操作：用户 {user_id} 不存在或已被删除")
        except (ImportError, Exception) as e:
            logging.warning(f"封号操作依赖于成员A的SysUser模型，暂不可用: {e}")

        # 记录审计日志
        await self.write_log(
            db=db, user_id=admin_id, action="ban",
            resource="user", resource_id=user_id,
            detail={"reason": reason},
        )
        return True

    # ==================== 审计日志 ====================

    async def write_log(
        self,
        db: AsyncSession,
        user_id: int,
        action: str,
        resource: str,
        resource_id: Optional[int] = None,
        detail: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        username: Optional[str] = None,
    ) -> SysAuditLog:
        """写入审计日志
        
        Args:
            db: 数据库会话
            user_id: 操作人ID
            username: 操作人用户名（冗余，防用户删除后丢失操作记录）
            action: 操作类型
            resource: 资源类型
            resource_id: 资源ID
            detail: 操作详情
            ip_address: 操作IP
            user_agent: User Agent
        """
        log = SysAuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource=resource,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)
        return log

    async def search_logs(self, db: AsyncSession, query: AuditLogSearchRequest) -> PageResult:
        """查询审计日志"""
        conditions = [True]

        if query.action:
            conditions.append(SysAuditLog.action == query.action)
        if query.resource:
            conditions.append(SysAuditLog.resource == query.resource)
        if query.user_id is not None:
            conditions.append(SysAuditLog.user_id == query.user_id)
        if query.start_time:
            conditions.append(SysAuditLog.created_at >= query.start_time)
        if query.end_time:
            conditions.append(SysAuditLog.created_at <= query.end_time)

        # 总数
        count_query = select(func.count()).select_from(SysAuditLog).where(*conditions)
        total = (await db.execute(count_query)).scalar() or 0

        # 分页查询
        sql_query = (
            select(SysAuditLog)
            .where(*conditions)
            .order_by(SysAuditLog.created_at.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        result = await db.execute(sql_query)
        items = result.scalars().all()

        return PageResult(
            items=[item for item in items],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )


# 全局单例
compliance_service = ComplianceService()