"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.exception_handler import global_exception_handler
from app.api.v1 import v1_router
from app.config import settings
from app.core.database import async_session_factory
from app.core.redis import init_redis, close_redis
from app.core.elasticsearch import init_elasticsearch, close_elasticsearch
from app.scheduler.crawler_scheduler import crawler_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting platform...")

    await init_redis()
    await init_elasticsearch()

    # 初始化爬虫调度器并加载所有定时任务
    await crawler_scheduler.init()
    async with async_session_factory() as db:
        try:
            count = await crawler_scheduler.load_all_from_db(db)
            logger.info(f"爬虫调度器已加载 {count} 个任务")
        except Exception as e:
            logger.warning(f"加载爬虫定时任务失败（DB 可能未就绪）: {e}")

    # Ensure uploads directory exists for file upload feature (member C)
    import os
    os.makedirs("uploads", exist_ok=True)

    yield

    await crawler_scheduler.shutdown()
    await close_elasticsearch()
    await close_redis()
    logger


# Static files for uploaded content (member C - IM file upload)
app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 中间件注册
app.add_middleware(RateLimitMiddleware)

# 全局异常处理器
app.add_exception_handler(Exception, global_exception_handler)

# Mount static file serving for uploads directory
# StaticFiles 在 import 阶段就校验目录是否存在，必须在此之前创建
import os
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Register routes
app.include_router(v1_router)


@app.get("/")
async def root():
    return {"message": "LLM Chat Platform API"}


@app.get("/health")
async def health():
    return {"status": "ok"}
