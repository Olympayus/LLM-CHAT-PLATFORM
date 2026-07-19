"""IM 业务逻辑服务（成员C）

提供好友管理、群组管理、消息历史查询等业务逻辑。
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.im import ImContact, ImGroup, ImGroupMember, ImMessage
from app.im.chat_history import chat_history_manager


class IMService:
    """IM 业务服务"""

    # ==================== 联系人/好友 ====================

    @staticmethod
    async def get_contacts(db: AsyncSession, user_id: int) -> List[ImContact]:
        query = (
            select(ImContact)
            .where(ImContact.user_id == user_id, ImContact.is_deleted == 0)
            .order_by(ImContact.created_at.desc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def add_contact(db: AsyncSession, user_id: int, contact_user_id: int, alias: Optional[str] = None) -> Optional[ImContact]:
        query = select(ImContact).where(
            ImContact.user_id == user_id,
            ImContact.contact_user_id == contact_user_id,
            ImContact.is_deleted == 0,
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        contact = ImContact(user_id=user_id, contact_user_id=contact_user_id, alias=alias)
        db.add(contact)
        reverse = ImContact(user_id=contact_user_id, contact_user_id=user_id)
        db.add(reverse)
        await db.flush()
        await db.refresh(contact)
        return contact

    @staticmethod
    async def delete_contact(db: AsyncSession, user_id: int, contact_id: int) -> bool:
        query = select(ImContact).where(
            ImContact.id == contact_id, ImContact.user_id == user_id, ImContact.is_deleted == 0
        )
        result = await db.execute(query)
        contact = result.scalar_one_or_none()
        if not contact:
            return False
        contact.is_deleted = 1
        reverse_query = select(ImContact).where(
            ImContact.user_id == contact.contact_user_id,
            ImContact.contact_user_id == user_id,
            ImContact.is_deleted == 0,
        )
        reverse_result = await db.execute(reverse_query)
        reverse_contact = reverse_result.scalar_one_or_none()
        if reverse_contact:
            reverse_contact.is_deleted = 1
        await db.flush()
        return True

    # ==================== 群组 ====================

    @staticmethod
    async def create_group(
        db: AsyncSession, group_name: str, owner_id: int,
        avatar_url: Optional[str] = None, notice: Optional[str] = None,
        member_ids: Optional[List[int]] = None,
    ) -> ImGroup:
        group = ImGroup(
            group_name=group_name, owner_id=owner_id,
            avatar_url=avatar_url, notice=notice,
            member_count=1 + len(member_ids or []),
        )
        db.add(group)
        await db.flush()
        await db.refresh(group)

        owner_member = ImGroupMember(group_id=group.id, user_type="user", user_id=owner_id, role="owner")
        db.add(owner_member)

        if member_ids:
            for uid in member_ids:
                if uid == owner_id:
                    continue
                member = ImGroupMember(group_id=group.id, user_type="user", user_id=uid, role="member")
                db.add(member)
        await db.flush()
        return group

    @staticmethod
    async def update_group(db: AsyncSession, group_id: int, user_id: int, **kwargs) -> Optional[ImGroup]:
        if not await IMService._is_group_owner_or_admin(db, group_id, user_id):
            return None
        query = select(ImGroup).where(ImGroup.id == group_id, ImGroup.status == 1, ImGroup.is_deleted == 0)
        result = await db.execute(query)
        group = result.scalar_one_or_none()
        if not group:
            return None
        allowed_fields = {"group_name", "avatar_url", "notice", "is_bot_enabled", "is_muted_all"}
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(group, key, value)
        await db.flush()
        await db.refresh(group)
        return group

    @staticmethod
    async def disband_group(db: AsyncSession, group_id: int, user_id: int) -> bool:
        query = select(ImGroup).where(ImGroup.id == group_id, ImGroup.owner_id == user_id, ImGroup.is_deleted == 0)
        result = await db.execute(query)
        group = result.scalar_one_or_none()
        if not group:
            return False
        group.status = 0
        group.is_deleted = 1
        await db.flush()
        return True

    @staticmethod
    async def get_user_groups(db: AsyncSession, user_id: int) -> List[ImGroup]:
        member_query = select(ImGroupMember.group_id).where(
            ImGroupMember.user_id == user_id, ImGroupMember.user_type == "user"
        )
        result = await db.execute(member_query)
        group_ids = [row[0] for row in result.all()]
        if not group_ids:
            return []
        group_query = (
            select(ImGroup)
            .where(ImGroup.id.in_(group_ids), ImGroup.status == 1, ImGroup.is_deleted == 0)
            .order_by(ImGroup.updated_at.desc())
        )
        result = await db.execute(group_query)
        return list(result.scalars().all())

    @staticmethod
    async def get_group_detail(db: AsyncSession, group_id: int) -> Optional[ImGroup]:
        query = select(ImGroup).where(ImGroup.id == group_id, ImGroup.status == 1, ImGroup.is_deleted == 0)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_group_members(db: AsyncSession, group_id: int) -> List[ImGroupMember]:
        query = select(ImGroupMember).where(ImGroupMember.group_id == group_id).order_by(ImGroupMember.joined_at.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def add_group_members(db: AsyncSession, group_id: int, operator_id: int, user_type: str, user_ids: List[int]) -> bool:
        if not await IMService._is_group_owner_or_admin(db, group_id, operator_id):
            return False
        count_query = select(func.count(ImGroupMember.id)).where(ImGroupMember.group_id == group_id)
        current_count = await db.scalar(count_query) or 0
        group_query = select(ImGroup).where(ImGroup.id == group_id)
        result = await db.execute(group_query)
        group = result.scalar_one_or_none()
        if not group or current_count + len(user_ids) > group.max_members:
            return False
        added = 0
        for uid in user_ids:
            check_query = select(ImGroupMember).where(
                ImGroupMember.group_id == group_id, ImGroupMember.user_type == user_type, ImGroupMember.user_id == uid
            )
            check_result = await db.execute(check_query)
            if check_result.scalar_one_or_none():
                continue
            member = ImGroupMember(group_id=group_id, user_type=user_type, user_id=uid, role="member")
            db.add(member)
            added += 1
        if added > 0:
            group.member_count = current_count + added
        await db.flush()
        return True

    @staticmethod
    async def remove_group_member(db: AsyncSession, group_id: int, member_id: int, operator_id: int) -> bool:
        if not await IMService._is_group_owner_or_admin(db, group_id, operator_id):
            return False
        query = select(ImGroupMember).where(ImGroupMember.id == member_id, ImGroupMember.group_id == group_id)
        result = await db.execute(query)
        member = result.scalar_one_or_none()
        if not member or member.role == "owner":
            return False
        await db.delete(member)
        group_query = select(ImGroup).where(ImGroup.id == group_id)
        group_result = await db.execute(group_query)
        group = group_result.scalar_one_or_none()
        if group and group.member_count > 0:
            group.member_count -= 1
        await db.flush()
        return True

    @staticmethod
    async def leave_group(db: AsyncSession, group_id: int, user_id: int) -> bool:
        query = select(ImGroupMember).where(
            ImGroupMember.group_id == group_id, ImGroupMember.user_id == user_id, ImGroupMember.user_type == "user"
        )
        result = await db.execute(query)
        member = result.scalar_one_or_none()
        if not member or member.role == "owner":
            return False
        await db.delete(member)
        group_query = select(ImGroup).where(ImGroup.id == group_id)
        group_result = await db.execute(group_query)
        group = group_result.scalar_one_or_none()
        if group and group.member_count > 0:
            group.member_count -= 1
        await db.flush()
        return True

    # ==================== 消息历史 ====================

    @staticmethod
    async def get_private_history(db: AsyncSession, user_id: int, other_user_id: int, page: int = 1, page_size: int = 20) -> Tuple[List[ImMessage], int]:
        return await chat_history_manager.get_private_history(db, user_id, other_user_id, page, page_size)

    @staticmethod
    async def get_group_history(db: AsyncSession, group_id: int, user_id: int, page: int = 1, page_size: int = 20) -> Tuple[List[ImMessage], int]:
        member_query = select(ImGroupMember).where(ImGroupMember.group_id == group_id, ImGroupMember.user_id == user_id)
        result = await db.execute(member_query)
        if not result.scalar_one_or_none():
            return [], 0
        return await chat_history_manager.get_group_history(db, group_id, page, page_size)

    @staticmethod
    async def get_offline_messages(db: AsyncSession, user_id: int, last_msg_id: Optional[int] = None, limit: int = 50) -> Tuple[List[ImMessage], bool]:
        return await chat_history_manager.get_offline_messages(db, user_id, last_msg_id, limit)

    @staticmethod
    async def mark_message_read(db: AsyncSession, message_id: int, user_id: int) -> bool:
        return await chat_history_manager.mark_as_read(db, message_id, user_id)

    # ==================== 内部辅助 ====================

    @staticmethod
    async def _is_group_owner_or_admin(db: AsyncSession, group_id: int, user_id: int) -> bool:
        query = select(ImGroupMember).where(
            ImGroupMember.group_id == group_id,
            ImGroupMember.user_id == user_id,
            ImGroupMember.user_type == "user",
            ImGroupMember.role.in_(["owner", "admin"]),
        )
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def is_group_member(db: AsyncSession, group_id: int, user_id: int) -> bool:
        query = select(ImGroupMember).where(ImGroupMember.group_id == group_id, ImGroupMember.user_id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None


im_service = IMService()