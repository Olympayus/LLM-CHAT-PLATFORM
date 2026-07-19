"""NL2SQL 智能问数业务服务

编排完整流程: 问数 → 生成 SQL → 安全校验 → 沙箱执行 → 数据解读 → 记录历史
"""

import time
from typing import Any, Optional

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.nl2sql import Nl2sqlEngine, nl2sql_engine
from app.models.nl2sql import Nl2sqlFavorite, Nl2sqlQueryHistory
from app.sandbox.executor import SqlSandboxExecutor, sql_executor
from app.sandbox.sql_validator import SqlValidator, sql_validator
from app.schemas.nl2sql import (
    ChartRecommendation,
    FavoriteCreateRequest,
    Nl2sqlAskRequest,
    Nl2sqlAskResponse,
    QueryHistoryItem,
    SqlValidationResult,
    TableSchema,
)


class Nl2sqlService:
    """NL2SQL 业务服务"""

    def __init__(
        self,
        engine: Optional[Nl2sqlEngine] = None,
        validator: Optional[SqlValidator] = None,
        executor: Optional[SqlSandboxExecutor] = None,
    ):
        self.engine = engine or nl2sql_engine
        self.validator = validator or sql_validator
        self.executor = executor or sql_executor

    async def ask(
        self,
        request: Nl2sqlAskRequest,
        user_id: int,
        db: Optional[AsyncSession] = None,
    ) -> Nl2sqlAskResponse:
        """智能问数完整流程

        Args:
            request: 问数请求
            user_id: 用户ID
            db: 数据库会话（用于记录历史）

        Returns:
            Nl2sqlAskResponse: 问数响应
        """
        question = request.question.strip()

        # 1. 生成 SQL
        logger.info(f"NL2SQL 问数: user_id={user_id}, question='{question}'")

        try:
            tables = None
            if db is not None:
                tables = await self.engine.read_schema(db, request.database_name)
            sql = await self.engine.generate_sql(
                question=question,
                tables=tables,
                database_name=request.database_name,
                db_session=db,
            )
        except Exception as e:
            logger.error(f"SQL 生成失败: {e}")
            return Nl2sqlAskResponse(
                question=question,
                generated_sql="",
                validation=SqlValidationResult(
                    is_valid=False,
                    is_readonly=True,
                    sql_type="UNKNOWN",
                    error=f"SQL 生成失败: {str(e)}",
                ),
                error_message=str(e),
            )

        # 2. 安全校验
        validation = self.validator.validate(sql)

        # 3. 执行 SQL（如果通过校验且需要执行）
        columns = None
        rows = None
        row_count = None
        execution_time_ms = None
        error_message = None

        if validation.is_valid and request.execute_sql:
            try:
                result = await self.executor.execute(sql)
                columns = result.get("columns")
                rows = result.get("rows")
                row_count = result.get("row_count")
                execution_time_ms = result.get("execution_time_ms")
                error_message = result.get("error")
            except Exception as e:
                logger.error(f"SQL 执行失败: {e}")
                error_message = str(e)
        elif not validation.is_valid:
            error_message = validation.error

        # 4. 图表推荐
        chart_recommendation = None
        if columns and rows:
            chart_recommendation = self.engine.recommend_chart(
                columns=columns,
                rows=rows,
                question=question,
            )

        # 5. AI 数据解读
        interpretation = None
        if (
            request.need_interpretation
            and columns
            and rows
            and not error_message
        ):
            try:
                interpretation = await self.engine.interpret_results(
                    question=question,
                    sql=sql,
                    columns=columns,
                    rows=rows,
                )
            except Exception as e:
                logger.error(f"数据解读失败: {e}")
                interpretation = None

        # 6. 记录查询历史（如果有 db）
        if db is not None:
            try:
                history = Nl2sqlQueryHistory(
                    user_id=user_id,
                    question=question,
                    generated_sql=sql,
                    is_valid=1 if validation.is_valid else -1,
                    execution_time_ms=execution_time_ms,
                    result_rows=row_count,
                    error_message=error_message,
                    chart_type=chart_recommendation.chart_type if chart_recommendation else None,
                    interpretation=interpretation,
                )
                db.add(history)
                await db.commit()
            except Exception as e:
                logger.error(f"保存查询历史失败: {e}")

        return Nl2sqlAskResponse(
            question=question,
            generated_sql=sql,
            validation=validation,
            execution_time_ms=execution_time_ms,
            columns=columns,
            rows=rows,
            row_count=row_count,
            chart_recommendation=chart_recommendation,
            interpretation=interpretation,
            error_message=error_message,
        )

    async def get_history(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        db: AsyncSession = None,
    ) -> dict:
        """获取查询历史列表"""
        if db is None:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
            }

        query = select(Nl2sqlQueryHistory).where(
            Nl2sqlQueryHistory.user_id == user_id
        )

        if keyword:
            query = query.where(
                Nl2sqlQueryHistory.question.ilike(f"%{keyword}%")
            )

        # 获取总数
        count_query = select(Nl2sqlQueryHistory.id).where(
            Nl2sqlQueryHistory.user_id == user_id
        )
        if keyword:
            count_query = count_query.where(
                Nl2sqlQueryHistory.question.ilike(f"%{keyword}%")
            )

        total_result = await db.execute(count_query)
        total = len(total_result.fetchall())

        # 分页查询
        query = query.order_by(desc(Nl2sqlQueryHistory.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "items": [item.to_dict() for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        }

    async def get_history_detail(
        self,
        history_id: int,
        user_id: int,
        db: AsyncSession = None,
    ) -> Optional[dict]:
        """获取查询历史详情"""
        if db is None:
            return None

        query = select(Nl2sqlQueryHistory).where(
            Nl2sqlQueryHistory.id == history_id,
            Nl2sqlQueryHistory.user_id == user_id,
        )
        result = await db.execute(query)
        history = result.scalar_one_or_none()

        if history is None:
            return None

        detail = history.to_dict()

        # 重新执行 SQL 获取最新数据
        if history.generated_sql and history.is_valid == 1:
            try:
                exec_result = await self.executor.execute(history.generated_sql)
                detail["columns"] = exec_result.get("columns")
                detail["rows"] = exec_result.get("rows")
            except Exception:
                detail["columns"] = None
                detail["rows"] = None

        return detail

    async def delete_history(
        self,
        ids: list[int],
        user_id: int,
        db: AsyncSession = None,
    ) -> int:
        """删除查询历史"""
        if db is None:
            return 0

        query = select(Nl2sqlQueryHistory).where(
            Nl2sqlQueryHistory.id.in_(ids),
            Nl2sqlQueryHistory.user_id == user_id,
        )
        result = await db.execute(query)
        items = result.scalars().all()

        for item in items:
            await db.delete(item)

        await db.commit()
        return len(items)

    async def get_schema_info(
        self,
        database_name: str = "llm_platform",
        db: AsyncSession = None,
    ) -> dict:
        """获取数据库 Schema 信息"""
        tables = await self.engine.read_schema(db, database_name)
        return {
            "tables": [t.model_dump() for t in tables],
            "table_count": len(tables),
        }

    # ==================== 收藏功能 ====================

    async def create_favorite(
        self,
        request: FavoriteCreateRequest,
        user_id: int,
        db: AsyncSession = None,
    ) -> Optional[dict]:
        """创建收藏"""
        if db is None:
            return None

        # 获取查询历史
        query = select(Nl2sqlQueryHistory).where(
            Nl2sqlQueryHistory.id == request.query_history_id,
            Nl2sqlQueryHistory.user_id == user_id,
        )
        result = await db.execute(query)
        history = result.scalar_one_or_none()

        if history is None:
            return None

        favorite = Nl2sqlFavorite(
            user_id=user_id,
            query_history_id=history.id,
            question=history.question,
            sql=history.generated_sql,
            chart_type=history.chart_type,
            note=request.note,
        )
        db.add(favorite)
        await db.commit()
        await db.refresh(favorite)

        return favorite.to_dict()

    async def get_favorites(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        db: AsyncSession = None,
    ) -> dict:
        """获取收藏列表"""
        if db is None:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
            }

        query = select(Nl2sqlFavorite).where(
            Nl2sqlFavorite.user_id == user_id
        )

        # 获取总数
        total_result = await db.execute(
            select(Nl2sqlFavorite.id).where(Nl2sqlFavorite.user_id == user_id)
        )
        total = len(total_result.fetchall())

        # 分页查询
        query = query.order_by(desc(Nl2sqlFavorite.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "items": [item.to_dict() for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        }

    async def delete_favorite(
        self,
        favorite_id: int,
        user_id: int,
        db: AsyncSession = None,
    ) -> bool:
        """删除收藏"""
        if db is None:
            return False

        query = select(Nl2sqlFavorite).where(
            Nl2sqlFavorite.id == favorite_id,
            Nl2sqlFavorite.user_id == user_id,
        )
        result = await db.execute(query)
        favorite = result.scalar_one_or_none()

        if favorite is None:
            return False

        await db.delete(favorite)
        await db.commit()
        return True

    async def update_favorite_note(
        self,
        favorite_id: int,
        note: str,
        user_id: int,
        db: AsyncSession = None,
    ) -> Optional[dict]:
        """更新收藏备注"""
        if db is None:
            return None

        query = select(Nl2sqlFavorite).where(
            Nl2sqlFavorite.id == favorite_id,
            Nl2sqlFavorite.user_id == user_id,
        )
        result = await db.execute(query)
        favorite = result.scalar_one_or_none()

        if favorite is None:
            return None

        favorite.note = note
        await db.commit()
        await db.refresh(favorite)

        return favorite.to_dict()


# 全局单例
nl2sql_service = Nl2sqlService()