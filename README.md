# 企业智能协同平台 (LLM Chat Platform)

## 项目简介

企业智能协同平台是一套企业级私有化部署的 AI 数据中台，实现从数据采集、清洗、分析到智能问数与协同办公的完整闭环。核心目标是赋能业务人员，通过自然语言与 AI 数字员工交互，降低数据获取与分析门槛，同时通过内置的即时通讯（IM）能力，打造企业内部的"数据+人员+AI"协同工作平台。

**关键设计决策：**
- 后端由六名成员各自负责模块，前端统一由成员D实现
- 成员F维护前端共享组件库（布局、表格、表单、上传等）供D复用
- 成员F维护所有公共基础设施（数据库、Redis/ES、Docker、CI/CD、部署）

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI 0.115+ | 异步高性能，原生 WebSocket 支持 |
| 前端框架 | Vue 3 + Element Plus + Pinia + TypeScript | D负责实现，F维护共享组件 |
| 数据库 | MySQL 5.7.26 | 关系型主库，存储所有业务数据 |
| 缓存 | Redis 7.x | 会话缓存、在线状态、消息队列、API限流 |
| 搜索引擎 | Elasticsearch 8.x | 亿级 IM 消息秒级检索 |
| 大模型 | 阿里百炼 (DashScope) | 兼容 OpenAI API 规范 |
| 实时通讯 | WebSocket | 消息端到端延迟 <200ms |
| ORM | SQLAlchemy 2.0 (async) | 异步数据库操作 |
| 数据验证 | Pydantic v2 | 请求/响应模型验证 |
| 任务调度 | APScheduler | 爬虫定时调度 |
| 沙箱执行 | RestrictedPython | SQL / Python 代码安全执行 |
| 包管理 | uv | Rust 编写的高速 Python 包管理器 |
| 反向代理 | Nginx | SSL 终端、静态资源、负载均衡 |
| 进程管理 | Gunicorn + Uvicorn Workers | 生产环境多进程 |
| CI/CD | GitHub Actions | 代码检查 + 自动构建 + 部署 |

## 项目结构

```
LLM-Chat-Platform/
├── app/                          # 后端应用
│   ├── main.py                   # FastAPI 应用工厂 + 生命周期
│   ├── config.py                 # pydantic-settings 配置
│   ├── middleware/               # 中间件（CORS、限流、异常处理）
│   ├── core/                     # 核心基础设施（F维护）
│   ├── models/                   # SQLAlchemy ORM 模型（30表）
│   ├── schemas/                  # Pydantic 请求/响应模型
│   ├── api/v1/                   # API 路由层
│   ├── services/                 # 业务逻辑层
│   ├── ai/                       # AI 引擎（LLM客户端、NL2SQL、技能生成、Agent）
│   ├── im/                       # IM 实时通讯引擎（WebSocket、消息处理、在线状态）
│   ├── sandbox/                  # 沙箱安全执行（RestrictedPython、SQL校验）
│   ├── scheduler/                # 定时任务（爬虫调度）
│   └── utils/                    # 工具函数（响应、分页、敏感词过滤、导出、邮件）
├── frontend/                     # 前端项目（Vue3，D负责，F维护共享组件）
├── nginx/                        # Nginx 配置（SSL + 反向代理 + 静态资源）
├── deploy/                       # 部署脚本（Dockerfile、生产Compose、备份）
├── alembic/                      # 数据库迁移
├── .github/workflows/            # GitHub Actions（CI + 自动部署）
├── tests/                        # 测试
└── scripts/                      # DDL建表 + 种子数据
```

## 快速开始

### 前置条件

- Python 3.11+
- Docker Desktop（推荐，一键启动 MySQL + Redis + ES）
- Node.js 18+（前端）

### 安装步骤

```bash
# 1. 克隆项目
git clone <repo-url>
cd LLM-Chat-Platform

# 2. 创建虚拟环境并安装依赖
pip install uv
uv sync

# 3. 启动基础设施（Docker）
docker-compose up -d

# 4. 配置环境变量
cp .env.example .env

# 5. 数据库迁移
alembic upgrade head

# 6. 启动后端
uvicorn app.main:app --reload

# 7. 启动前端（另一个终端）
cd frontend
npm install
npm run dev
```

## 页面功能

### 用户端（7个页面）

| 页面 | 后端负责人 | 优先级 | 功能 |
|------|:----------:|:------:|------|
| 登录/注册/忘记密码 | A | P0 | 账号密码登录、注册、忘记密码、7天免登录 |
| 控制台首页 | F | P0 | 快捷入口、最近会话、待办事项、数据卡片 |
| 个人中心 | A | P1 | 个人资料、修改密码、通知偏好、登录历史 |
| 通知中心 | C | P1 | 通知列表、分类筛选、已读/未读、导航红点 |
| IM 聊天页 | C | P0 | 会话列表、消息气泡、已读回执、正在输入、ES检索 |
| NL2SQL 问数页 | E | P0 | 自然语言转SQL、表格+图表、SSE流式、历史收藏 |
| 文件管理 | F | P1 | 文件上传/下载/分享、分类筛选、存储配额 |

### 管理端（12个页面）

| 页面 | 后端负责人 | 优先级 | 功能 |
|------|:----------:|:------:|------|
| 管理控制台 | F | P0 | 系统概览、趋势图、爬虫/模型/存储统计 |
| 用户管理 | A | P0 | 用户CRUD、状态管理、角色分配、批量导入 |
| 部门管理 | A | P0 | 部门树、CRUD、成员查看 |
| 角色管理 | A | P0 | 角色CRUD、树形权限分配、成员查看 |
| 菜单/权限管理 | A | P0 | 菜单树（目录/菜单/按钮三级）、权限标识 |
| 模型管理 | B | P0 | 模型CRUD、连通性测试、参数配置 |
| 技能管理 | B | P1 | 技能CRUD、AI辅助生成、技能测试 |
| 数字员工管理 | B | P1 | 员工CRUD、技能绑定、在线测试对话 |
| 爬虫任务管理 | F | P1 | 任务CRUD、执行控制、日志、清洗规则 |
| 合规审计 | D | P1 | 敏感词、群组管理、消息穿透查询、撤回、禁言封号 |
| 审计日志 | D | P1 | 日志列表、搜索筛选、导出 |
| 系统设置 | F | P1 | 站点信息、存储、登录策略、日志策略、SMTP |

## 功能模块（后端）

| 编号 | 模块 | 负责人 | 接口数 | 核心表 |
|:----:|------|:------:|:------:|--------|
| F-00 | 注册登录 + Token刷新 | A | 9 | sys_user |
| F-01 | 用户/部门/角色/菜单 | A | 18 | 6 张认证表 |
| F-PF | 个人中心 | A | 5 | sys_user |
| F-02 | 模型管理 | B | 7 | model_config |
| F-03 | NL2SQL + 沙箱 | E | 10 | nl2sql_query_history |
| F-04 | 爬虫 + 数据清洗 | F | 13 | 3 张爬虫表 |
| F-05 | 技能管理 | B | 8 | skill |
| F-06 | 数字员工管理 | B | 9 | digital_employee |
| F-07 | IM后端 + 通知中心 | C | 16 + WS | 7 张 IM/通知表 |
| F-08 | 合规审计 | D | 19 | im_sensitive_word |
| F-DB | 控制台/仪表盘 | F | 4 | 多表聚合 |
| F-FL | 文件管理 | F | 7 | file_record |
| F-SC | 系统设置 | F | 4 | sys_config |

## 团队分工

| 成员 | 模块 | 后端职责 | 前端 | 表数 |
|:----:|:-----|:---------|:----:|:----:|
| A | F-00, F-01, F-PF | 认证、用户、部门、角色、菜单、个人中心、密码重置 | — | 8 |
| B | F-02, F-05, F-06 | 模型、技能、数字员工、LLM客户端、Agent | — | 6 |
| C | F-07, F-NT | IM后端、WebSocket、消息处理、通知中心 | — | 7 |
| D | F-08 | 合规审计、敏感词、ES检索 | 全部 22 个前端页面 | 2 |
| E | F-03 | NL2SQL引擎、RestrictedPython沙箱、SSE | — | 2 |
| F | F-04, F-DB, F-FL, F-SC | 爬虫、控制台、文件、系统设置、基础设施 | 共享组件库(8个) | 6 |

## 开发规范

- **代码风格**: 遵循 PEP 8，使用 `ruff` 检查
- **提交规范**: `<type>(<scope>): <subject>` — feat/fix/docs/refactor/chore
- **分支策略**: `main` / `develop` / `feature/*`
- **API 设计**: RESTful，统一响应 `{"code":0,"message":"ok","data":{}}`
- **数据库**: 所有表包含 `id`, `created_at`, `updated_at`, `is_deleted`

## 开发阶段

| 阶段 | 周次 | 核心目标 |
|:----:|:----:|----------|
| 一 | 1-2 | 基础设施、认证模块、前端布局和路由守卫 |
| 二 | 3-6 | 用户管理、模型、IM、NL2SQL、爬虫 + 前端页面 |
| 三 | 7-9 | Agent引擎、合规审计、通知中心、文件管理、系统设置 |
| 四 | 10-12 | 集成测试、压测、生产部署、Bug修复 |

## License

Proprietary — 企业内部使用
