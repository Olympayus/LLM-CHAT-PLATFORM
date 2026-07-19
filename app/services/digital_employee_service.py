"""数字员工管理业务逻辑"""

from typing import Optional

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LLMClient, LLMClientFactory
from app.ai.agent_executor import AgentExecutor
from app.models.digital_employee import DigitalEmployee, EmployeeSkillRel
from app.models.skill import Skill as SkillModel
from app.schemas.digital_employee import DigitalEmployeeCreate, DigitalEmployeeUpdate


class DigitalEmployeeService:
    """数字员工 CRUD + 技能绑定 + 测试对话"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_employee(self, data: DigitalEmployeeCreate, created_by: Optional[int] = None) -> DigitalEmployee:
        """创建数字员工"""
        employee = DigitalEmployee(
            name=data.name,
            avatar_url=data.avatar_url,
            role_description=data.role_description,
            model_id=data.model_id,
            system_prompt=data.system_prompt,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
            is_enabled=1 if data.is_enabled else 0,
            created_by=created_by,
        )
        self.db.add(employee)
        await self.db.flush()

        # 绑定技能
        if data.skill_ids:
            for skill_id in data.skill_ids:
                rel = EmployeeSkillRel(employee_id=employee.id, skill_id=skill_id)
                self.db.add(rel)

        await self.db.flush()
        await self.db.refresh(employee)
        logger.info(f"创建数字员工: {employee.name} (id={employee.id})")
        return employee

    async def get_employee(self, employee_id: int) -> Optional[DigitalEmployee]:
        """获取数字员工详情"""
        result = await self.db.execute(
            select(DigitalEmployee).where(
                DigitalEmployee.id == employee_id,
                DigitalEmployee.is_deleted == 0,
            )
        )
        return result.scalar_one_or_none()

    async def get_employees(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
    ) -> tuple[list[DigitalEmployee], int]:
        """获取数字员工列表（分页+搜索）"""
        query = select(DigitalEmployee).where(DigitalEmployee.is_deleted == 0)

        if keyword:
            query = query.where(DigitalEmployee.name.ilike(f"%{keyword}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            query
            .order_by(DigitalEmployee.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        employees = list(result.scalars().all())

        return employees, total

    async def update_employee(self, employee_id: int, data: DigitalEmployeeUpdate) -> Optional[DigitalEmployee]:
        """更新数字员工"""
        employee = await self.get_employee(employee_id)
        if not employee:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "is_enabled":
                setattr(employee, field, 1 if value else 0)
            else:
                setattr(employee, field, value)

        await self.db.flush()
        await self.db.refresh(employee)
        logger.info(f"更新数字员工: {employee.name} (id={employee.id})")
        return employee

    async def delete_employee(self, employee_id: int) -> bool:
        """删除数字员工（软删除）"""
        employee = await self.get_employee(employee_id)
        if not employee:
            return False

        employee.is_deleted = 1
        await self.db.flush()
        logger.info(f"删除数字员工: id={employee_id}")
        return True

    async def toggle_status(self, employee_id: int, is_enabled: bool) -> Optional[DigitalEmployee]:
        """启用/禁用数字员工"""
        employee = await self.get_employee(employee_id)
        if not employee:
            return None

        employee.is_enabled = 1 if is_enabled else 0
        await self.db.flush()
        await self.db.refresh(employee)
        logger.info(f"切换数字员工状态: {employee.name} enabled={is_enabled}")
        return employee

    async def bind_skills(self, employee_id: int, skill_ids: list[int]) -> DigitalEmployee:
        """绑定技能（替换现有绑定）"""
        employee = await self.get_employee(employee_id)
        if not employee:
            raise ValueError(f"数字员工不存在: id={employee_id}")

        # 删除现有绑定
        existing = await self.db.execute(
            select(EmployeeSkillRel).where(EmployeeSkillRel.employee_id == employee_id)
        )
        for rel in existing.scalars().all():
            await self.db.delete(rel)

        # 创建新绑定
        for skill_id in skill_ids:
            rel = EmployeeSkillRel(employee_id=employee_id, skill_id=skill_id)
            self.db.add(rel)

        await self.db.flush()
        logger.info(f"绑定技能到数字员工 {employee_id}: {skill_ids}")
        return employee

    async def get_bound_skills(self, employee_id: int) -> list[SkillModel]:
        """获取数字员工绑定的技能列表"""
        result = await self.db.execute(
            select(SkillModel)
            .join(EmployeeSkillRel, EmployeeSkillRel.skill_id == SkillModel.id)
            .where(
                EmployeeSkillRel.employee_id == employee_id,
                SkillModel.is_deleted == 0,
            )
        )
        return list(result.scalars().all())

    async def test_chat(self, employee_id: int, message: str) -> dict:
        """测试对话"""
        employee = await self.get_employee(employee_id)
        if not employee:
            raise ValueError(f"数字员工不存在: id={employee_id}")

        # 获取绑定的模型
        from app.services.model_service import ModelService
        model_service = ModelService(self.db)
        model = await model_service.get_model(employee.model_id)
        if not model:
            raise ValueError(f"绑定的模型不存在: id={employee.model_id}")

        # 获取绑定的技能
        skills = await self.get_bound_skills(employee_id)
        skills_data = []
        for skill in skills:
            skills_data.append({
                "name": skill.name,
                "description": skill.description,
                "params_schema": skill.params_schema,
                "python_code": skill.python_code,
            })

        # 创建 LLM 客户端
        client = LLMClientFactory.create(
            base_url=model.base_url,
            api_key=model.api_key,
            model_id=model.model_id,
        )

        # 创建 Agent 执行器
        executor = AgentExecutor(
            client=client,
            system_prompt=employee.system_prompt,
            skills=skills_data if skills_data else None,
        )

        # 执行对话
        result = await executor.execute(user_message=message)

        # 保存对话记录
        from app.models.digital_employee import DigitalEmployeeConversation
        conversation = DigitalEmployeeConversation(
            employee_id=employee_id,
            user_id=0,  # TODO(成员A): 接入真实用户ID
            user_message=message,
            bot_response=result["reply"],
        )
        self.db.add(conversation)

        return {
            "reply": result["reply"],
            "model_id": model.id,
            "function_calls": result.get("function_calls", []),
        }

    async def get_conversations(self, employee_id: int, page: int = 1, page_size: int = 20) -> tuple[list, int]:
        """获取数字员工对话记录"""
        from app.models.digital_employee import DigitalEmployeeConversation
        query = select(DigitalEmployeeConversation).where(
            DigitalEmployeeConversation.employee_id == employee_id
        )
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(DigitalEmployeeConversation.id.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
