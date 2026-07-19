"""技能管理业务逻辑"""

from typing import Optional

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LLMClient, LLMClientFactory
from app.ai.skill_generator import SkillGenerator
from app.models.skill import Skill, SkillParam
from app.schemas.skill import SkillCreate, SkillUpdate


class SkillService:
    """技能 CRUD + AI 辅助生成"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_skill(self, data: SkillCreate, created_by: Optional[int] = None) -> Skill:
        """创建技能"""
        skill = Skill(
            name=data.name,
            type=data.type,
            description=data.description,
            category=data.category,
            params_schema=data.params_schema,
            python_code=data.python_code,
            skill_md_content=data.skill_md_content,
            is_enabled=1 if data.is_enabled else 0,
            created_by=created_by,
        )
        self.db.add(skill)
        await self.db.flush()

        # 创建参数列表
        if data.params:
            for p in data.params:
                param = SkillParam(
                    skill_id=skill.id,
                    param_name=p.param_name,
                    param_type=p.param_type,
                    is_required=1 if p.is_required else 0,
                    description=p.description,
                    default_value=p.default_value,
                )
                self.db.add(param)

        await self.db.flush()
        await self.db.refresh(skill)
        logger.info(f"创建技能: {skill.name} (id={skill.id})")
        return skill

    async def get_skill(self, skill_id: int) -> Optional[Skill]:
        """获取技能详情"""
        result = await self.db.execute(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_deleted == 0,
            )
        )
        return result.scalar_one_or_none()

    async def get_skills(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        skill_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> tuple[list[Skill], int]:
        """获取技能列表（分页+搜索）"""
        query = select(Skill).where(Skill.is_deleted == 0)

        if category:
            query = query.where(Skill.category == category)
        if skill_type:
            query = query.where(Skill.type == skill_type)
        if keyword:
            query = query.where(
                Skill.name.ilike(f"%{keyword}%")
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            query
            .order_by(Skill.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        skills = list(result.scalars().all())

        return skills, total

    async def update_skill(self, skill_id: int, data: SkillUpdate) -> Optional[Skill]:
        """更新技能"""
        skill = await self.get_skill(skill_id)
        if not skill:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "is_enabled":
                setattr(skill, field, 1 if value else 0)
            else:
                setattr(skill, field, value)

        await self.db.flush()
        await self.db.refresh(skill)
        logger.info(f"更新技能: {skill.name} (id={skill.id})")
        return skill

    async def delete_skill(self, skill_id: int) -> bool:
        """删除技能（软删除）"""
        skill = await self.get_skill(skill_id)
        if not skill:
            return False

        skill.is_deleted = 1
        await self.db.flush()
        logger.info(f"删除技能: id={skill_id}")
        return True

    async def ai_generate_skill(
        self,
        requirement: str,
        model_id: int,
        skill_type: str,
    ) -> dict:
        """AI 辅助生成技能"""
        from app.services.model_service import ModelService

        model_service = ModelService(self.db)
        model = await model_service.get_model(model_id)
        if not model:
            raise ValueError(f"模型不存在: id={model_id}")

        client = LLMClientFactory.create(
            base_url=model.base_url,
            api_key=model.api_key,
            model_id=model.model_id,
        )

        generator = SkillGenerator(client)

        if skill_type == "function_call":
            result = await generator.generate_function_call_skill(requirement)
        elif skill_type == "skill_md":
            result = await generator.generate_skill_md(requirement)
        else:
            raise ValueError(f"不支持的技能类型: {skill_type}")

        logger.info(f"AI 生成技能完成: type={skill_type}")
        return {"skill_type": skill_type, **result} if isinstance(result, dict) else {"skill_type": skill_type, "full_content": result}

    async def test_skill(self, skill_id: int) -> tuple[bool, str]:
        """测试技能 — 在沙箱中执行 Python 代码并返回结果"""
        skill = await self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"技能不存在: id={skill_id}")
        if not skill.python_code:
            raise ValueError("该技能没有可执行代码")
        try:
            local_vars = {"params": {}}
            exec(skill.python_code, {"__builtins__": {}}, local_vars)
            if "execute" in local_vars:
                result = local_vars["execute"]({})
                return True, str(result)
            return True, str(local_vars)
        except Exception as e:
            return False, f"执行失败: {str(e)}"

    async def get_skill_params(self, skill_id: int) -> list[SkillParam]:
        """获取技能参数列表"""
        result = await self.db.execute(
            select(SkillParam).where(SkillParam.skill_id == skill_id)
        )
        return list(result.scalars().all())