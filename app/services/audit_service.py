"""审计日志服务（预留）"""

from typing import Optional


class AuditService:
    """审计日志服务"""

    @staticmethod
    async def log(
        user_id: int,
        action: str,
        target_type: str,
        target_id: int,
        detail: str,
        ip_address: Optional[str] = None,
        status: str = "success",
    ):
        """写入审计日志"""
        # TODO: 写入 sys_audit_log 表
        pass

    @staticmethod
    async def log_login(user_id: int, ip_address: str, status: str = "success"):
        """记录登录日志"""
        await AuditService.log(
            user_id=user_id,
            action="login",
            target_type="user",
            target_id=user_id,
            detail="用户登录",
            ip_address=ip_address,
            status=status,
        )

    @staticmethod
    async def log_create_user(operator_id: int, target_user_id: int):
        """记录创建用户"""
        await AuditService.log(
            user_id=operator_id,
            action="create_user",
            target_type="user",
            target_id=target_user_id,
            detail=f"创建用户(ID={target_user_id})",
        )

    @staticmethod
    async def log_delete_user(operator_id: int, target_user_id: int):
        """记录删除用户"""
        await AuditService.log(
            user_id=operator_id,
            action="delete_user",
            target_type="user",
            target_id=target_user_id,
            detail=f"删除用户(ID={target_user_id})",
        )

    @staticmethod
    async def log_assign_role(operator_id: int, target_user_id: int, role_ids: list):
        """记录分配角色"""
        await AuditService.log(
            user_id=operator_id,
            action="assign_role",
            target_type="user",
            target_id=target_user_id,
            detail=f"为用户(ID={target_user_id})分配角色: {role_ids}",
        )

    @staticmethod
    async def log_change_password(user_id: int):
        """记录修改密码"""
        await AuditService.log(
            user_id=user_id,
            action="change_password",
            target_type="user",
            target_id=user_id,
            detail="修改密码",
        )

    @staticmethod
    async def log_reset_password(operator_id: int, target_user_id: int):
        """记录重置密码"""
        await AuditService.log(
            user_id=operator_id,
            action="reset_password",
            target_type="user",
            target_id=target_user_id,
            detail=f"重置用户(ID={target_user_id})密码",
        )