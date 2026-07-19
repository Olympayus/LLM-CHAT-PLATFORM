"""企业智能协同平台 - 全局配置"""

import json

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类，从环境变量加载"""

    # 数据库
    DATABASE_URL: str = "mysql+aiomysql://root:root123@localhost:3306/llm_platform"
    DATABASE_URL_SYNC: str = "mysql+pymysql://root:root123@localhost:3306/llm_platform"
    # PyMySQL 同步连接 SSL：本地 MySQL 5.7 Docker 未配置证书，默认禁用。
    # 生产环境设置环境变量 PYMYSQL_SSL=true 以启用。
    PYMYSQL_SSL: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Elasticsearch
    ES_HOSTS: str = "http://localhost:9200"

    # 阿里百炼
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = '["http://localhost:5173","http://localhost:3000"]'

    # 日志
    LOG_LEVEL: str = "INFO"

    # =========================
    # 沙箱执行
    # =========================
    SANDBOX_IMAGE: str = "python:3.11-slim"
    SANDBOX_TIMEOUT: int = 30

    # =========================
    # 邮件
    # =========================
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@example.com"

    # =========================
    # 限流
    # =========================
    RATE_LIMIT_PER_MINUTE: int = 60

    # =========================
    # 文件上传
    # =========================
    UPLOAD_MAX_SIZE_MB: int = 50
    STORAGE_TYPE: str = "local"

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:5173"]

    @property
    def pymysql_connect_args(self) -> dict:
        """PyMySQL 同步连接参数：None 禁用 SSL（默认），True 启用 SSL（生产）"""
        return {"ssl": True if self.PYMYSQL_SSL else None}

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_ignore_empty=True,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
