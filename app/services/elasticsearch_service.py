"""Elasticsearch 消息检索服务

提供 IM 消息的索引、搜索和删除功能。
使用按月轮转索引: im_message_YYYY-MM
"""

import logging
from datetime import datetime
from typing import Optional

from app.core.elasticsearch import es_client
from app.schemas.im import MessageSearchRequest

# ES 索引映射
MESSAGE_INDEX_PREFIX = "im_message"

MESSAGE_MAPPING = {
    "mappings": {
        "properties": {
            "message_id": {"type": "long"},
            "chat_type": {"type": "keyword"},
            "sender_type": {"type": "keyword"},
            "sender_id": {"type": "long"},
            "group_id": {"type": "long"},
            "content": {"type": "text", "analyzer": "ik_smart"},
            "msg_type": {"type": "keyword"},
            "is_recalled": {"type": "boolean"},
            "created_at": {"type": "date"},
        }
    }
}


def _get_index_name(year: Optional[int] = None, month: Optional[int] = None) -> str:
    """获取按月轮转的索引名称"""
    now = datetime.now()
    y = year if year else now.year
    m = month if month else now.month
    return f"{MESSAGE_INDEX_PREFIX}_{y:04d}-{m:02d}"


class ElasticsearchService:
    """ES 消息检索服务"""

    async def initialize(self) -> None:
        """初始化 ES 连接并创建索引"""
        await es_client.init()
        # 创建当前月份的索引
        index_name = _get_index_name()
        await es_client.create_index_if_not_exists(index_name, MESSAGE_MAPPING)

    async def create_current_index(self) -> bool:
        """创建当前月份索引"""
        index_name = _get_index_name()
        return await es_client.create_index_if_not_exists(index_name, MESSAGE_MAPPING)

    async def index_message(self, message: dict) -> bool:
        """索引一条消息到 ES
        
        Args:
            message: 消息字典，包含 message_id, chat_type, sender_type, sender_id,
                    group_id, content, msg_type, is_recalled, created_at 等字段
        """
        try:
            index_name = _get_index_name()
            doc = {
                "message_id": message["message_id"],
                "chat_type": message.get("chat_type", "private"),
                "sender_type": message.get("sender_type", "user"),
                "sender_id": message.get("sender_id", 0),
                "group_id": message.get("group_id", 0),
                "content": message.get("content", ""),
                "msg_type": message.get("msg_type", "text"),
                "is_recalled": message.get("is_recalled", False),
                "created_at": message.get("created_at"),
            }
            response = await es_client.client.index(
                index=index_name,
                id=str(message["message_id"]),
                document=doc,
            )
            return response.get("result") in ("created", "updated")
        except Exception as e:
            # ES 写入失败不影响主流程，记录错误日志
            logging.error(f"ES index_message failed: {e}")
            return False

    async def bulk_index(self, messages: list[dict]) -> bool:
        """批量索引消息"""
        try:
            index_name = _get_index_name()
            bulk_body = []
            for msg in messages:
                bulk_body.append({"index": {"_index": index_name, "_id": str(msg["message_id"])}})
                bulk_body.append({
                    "message_id": msg["message_id"],
                    "chat_type": msg.get("chat_type", "private"),
                    "sender_type": msg.get("sender_type", "user"),
                    "sender_id": msg.get("sender_id", 0),
                    "group_id": msg.get("group_id", 0),
                    "content": msg.get("content", ""),
                    "msg_type": msg.get("msg_type", "text"),
                    "is_recalled": msg.get("is_recalled", False),
                    "created_at": msg.get("created_at"),
                })
            
            response = await es_client.client.bulk(body=bulk_body)
            return not response.get("errors", True)
        except Exception as e:
            logging.error(f"ES bulk_index failed: {e}")
            return False

    async def search_messages(self, query: MessageSearchRequest) -> dict:
        """搜索消息 - 多条件组合查询
        
        Returns:
            {"items": [...], "total": int, "page": int, "page_size": int}
        """
        must_clauses = []

        # 关键词搜索
        if query.keyword:
            must_clauses.append({
                "match": {"content": query.keyword}
            })

        # 发送者筛选
        if query.sender_id is not None:
            must_clauses.append({
                "term": {"sender_id": query.sender_id}
            })

        # 群组筛选
        if query.group_id is not None:
            must_clauses.append({
                "term": {"group_id": query.group_id}
            })

        # 会话类型筛选
        if query.chat_type:
            must_clauses.append({
                "term": {"chat_type": query.chat_type}
            })

        # 时间范围筛选
        if query.start_time or query.end_time:
            time_range = {}
            if query.start_time:
                time_range["gte"] = query.start_time.isoformat()
            if query.end_time:
                time_range["lte"] = query.end_time.isoformat()
            must_clauses.append({
                "range": {"created_at": time_range}
            })

        # 如果没有任何筛选条件，匹配所有
        if not must_clauses:
            must_clauses.append({"match_all": {}})

        search_body = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": [
                        {"term": {"is_recalled": False}}
                    ]
                }
            },
            "sort": [{"created_at": {"order": "desc"}}],
            "from": (query.page - 1) * query.page_size,
            "size": query.page_size,
        }

        try:
            index_name = _get_index_name()
            response = await es_client.client.search(
                index=index_name,
                body=search_body,
            )

            hits = response.get("hits", {})
            total = hits.get("total", {}).get("value", 0)
            items = []
            for hit in hits.get("hits", []):
                source = hit["_source"]
                items.append({
                    "id": source.get("message_id"),
                    "chat_type": source.get("chat_type"),
                    "sender_type": source.get("sender_type"),
                    "sender_id": source.get("sender_id"),
                    "group_id": source.get("group_id"),
                    "msg_type": source.get("msg_type"),
                    "content": source.get("content"),
                    "is_recalled": source.get("is_recalled", False),
                    "created_at": source.get("created_at"),
                })

            return {
                "items": items,
                "total": total,
                "page": query.page,
                "page_size": query.page_size,
            }
        except Exception as e:
            logging.error(f"ES search_messages failed: {e}")
            return {
                "items": [],
                "total": 0,
                "page": query.page,
                "page_size": query.page_size,
            }

    async def delete_by_message_id(self, message_id: int) -> bool:
        """根据消息ID删除 ES 文档（消息撤回时调用）"""
        try:
            index_name = _get_index_name()
            response = await es_client.client.delete(
                index=index_name,
                id=str(message_id),
                ignore=[404],  # 文档不存在也视为成功
            )
            return True
        except Exception as e:
            logging.error(f"ES delete_by_message_id failed: {e}")
            return False


# 全局单例
es_service = ElasticsearchService()