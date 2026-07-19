"""File storage models (F-FL) — Member F"""

from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class FileRecord(Base):
    __tablename__ = "file_record"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    original_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="原始文件名")
    stored_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="存储文件名")
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, comment="存储路径")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件大小(字节)")
    file_type: Mapped[str] = mapped_column(String(64), nullable=True, comment="MIME类型")
    category: Mapped[str] = mapped_column(String(32), nullable=True, comment="分类: image/document/code/other")
    md5: Mapped[str] = mapped_column(String(64), nullable=True, comment="文件MD5(去重)")
    upload_by: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="上传者ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    is_deleted: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="软删除")


class FileShare(Base):
    __tablename__ = "file_share"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件ID")
    share_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="分享码")
    password: Mapped[str] = mapped_column(String(128), nullable=True, comment="提取密码")
    expire_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, comment="过期时间")
    download_count: Mapped[int] = mapped_column(Integer, default=0, comment="下载次数")
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="分享者ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
