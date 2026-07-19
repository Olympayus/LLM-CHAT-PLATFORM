.PHONY: setup install dev-help init-db migrate run test clean

# ============================================================
# 企业智能协同平台 - Makefile
# ============================================================

VENV_DIR := .venv

# 检测操作系统
UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Linux)
	ACTIVATE := $(VENV_DIR)/bin/activate
	PYTHON := $(VENV_DIR)/bin/python
else ifeq ($(UNAME_S),Darwin)
	ACTIVATE := $(VENV_DIR)/bin/activate
	PYTHON := $(VENV_DIR)/bin/python
else
	ACTIVATE := $(VENV_DIR)/Scripts/activate
	PYTHON := $(VENV_DIR)/Scripts/python
endif

help:
	@echo "================================="
	@echo "企业智能协同平台 - 常用命令"
	@echo "================================="
	@echo "make setup   - 完整环境搭建 (venv + 安装依赖)"
	@echo "make install - 仅安装依赖 (已激活 venv 后使用)"
	@echo "make run     - 启动开发服务器"
	@echo "make migrate - 执行数据库迁移"
	@echo "make init-db - 初始化数据库 (MySQL)"
	@echo "make test    - 运行测试"
	@echo "make clean   - 清理缓存文件"

setup:
	python -m venv $(VENV_DIR)
	uv pip install -r requirements.txt
	@echo "================================="
	@echo "✅ 环境搭建完成！请执行:"
	@echo "   source $(ACTIVATE)  (Linux/Mac)"
	@echo "   或 $(VENV_DIR)\\Scripts\\activate  (Windows)"
	@echo "================================="

install:
	uv pip install -r requirements.txt
	@echo "✅ 依赖安装完成"

run:
	$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(message)"

init-db:
	mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS llm_platform DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
	@echo "✅ 数据库初始化完成"

test:
	$(PYTHON) -m pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf $(VENV_DIR)
	rm -rf .pytest_cache
	@echo "✅ 清理完成"
