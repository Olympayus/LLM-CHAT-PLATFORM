"""模型管理业务逻辑"""

from typing import Optional

from loguru import logger
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LLMClient, LLMClientFactory
from app.models.model_config import ModelConfig
from app.schemas.model_config import ModelConfigCreate, ModelConfigUpdate


class ModelService:
    """模型配置 CRUD + 连通性测试"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_model(self, data: ModelConfigCreate) -> ModelConfig:
        """创建模型配置"""
        # 如果设为默认，清除其他默认
        if data.is_default:
            await self._clear_default()

        model = ModelConfig(
            display_name=data.display_name,
            category=data.category,
            base_url=data.base_url,
            api_key=data.api_key,
            model_id=data.model_id,
            is_default=1 if data.is_default else 0,
            is_enabled=1 if data.is_enabled else 0,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
        )
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        logger.info(f"创建模型配置: {model.display_name} (id={model.id})")
        return model

    async def get_model(self, model_id: int) -> Optional[ModelConfig]:
        """获取模型详情"""
        result = await self.db.execute(
            select(ModelConfig).where(
                ModelConfig.id == model_id,
                ModelConfig.is_deleted == 0,
            )
        )
        return result.scalar_one_or_none()

    async def get_models(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> tuple[list[ModelConfig], int]:
        """获取模型列表（分页+搜索）"""
        query = select(ModelConfig).where(ModelConfig.is_deleted == 0)

        # 筛选条件
        if category:
            query = query.where(ModelConfig.category == category)
        if keyword:
            query = query.where(
                ModelConfig.display_name.ilike(f"%{keyword}%")
            )

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = (
            query
            .order_by(ModelConfig.is_default.desc(), ModelConfig.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        models = list(result.scalars().all())

        return models, total

    async def update_model(self, model_id: int, data: ModelConfigUpdate) -> Optional[ModelConfig]:
        """更新模型配置"""
        model = await self.get_model(model_id)
        if not model:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 如果设为默认，清除其他默认
        if update_data.get("is_default"):
            await self._clear_default(exclude_id=model_id)

        # 更新字段
        for field, value in update_data.items():
            if field == "is_default":
                setattr(model, field, 1 if value else 0)
            elif field == "is_enabled":
                setattr(model, field, 1 if value else 0)
            else:
                setattr(model, field, value)

        await self.db.flush()
        await self.db.refresh(model)
        logger.info(f"更新模型配置: {model.display_name} (id={model.id})")
        return model

    async def delete_model(self, model_id: int) -> bool:
        """删除模型配置（软删除）"""
        model = await self.get_model(model_id)
        if not model:
            return False

        model.is_deleted = 1
        await self.db.flush()
        logger.info(f"删除模型配置: id={model_id}")
        return True

    async def set_default(self, model_id: int) -> Optional[ModelConfig]:
        """设为默认模型"""
        model = await self.get_model(model_id)
        if not model:
            return None

        await self._clear_default(exclude_id=model_id)
        model.is_default = 1
        await self.db.flush()
        await self.db.refresh(model)
        logger.info(f"设置默认模型: {model.display_name} (id={model.id})")
        return model

    async def test_model(self, model_id: int) -> bool:
        """测试模型连通性"""
        model = await self.get_model(model_id)
        if not model:
            raise ValueError(f"模型不存在: id={model_id}")

        client = LLMClientFactory.create(
            base_url=model.base_url,
            api_key=model.api_key,
            model_id=model.model_id,
        )
        return await client.test_connection()

    async def _clear_default(self, exclude_id: Optional[int] = None) -> None:
        """清除所有默认标记"""
        query = select(ModelConfig).where(
            ModelConfig.is_default == 1,
            ModelConfig.is_deleted == 0,
        )
        if exclude_id:
            query = query.where(ModelConfig.id != exclude_id)

        result = await self.db.execute(query)
        for model in result.scalars().all():
            model.is_default = 0

    @staticmethod
    async def test_connection_direct(base_url: str, api_key: str, model_id: str) -> tuple[bool, str]:
        """直接测试连接（不通过数据库）"""
        try:
            client = LLMClient(base_url=base_url, api_key=api_key, model_id=model_id)
            result = await client.test_connection()
            if result:
                return True, "连接成功"
            return False, "模型返回空响应"
        except Exception as e:
            return False, f"连接失败: {str(e)}"