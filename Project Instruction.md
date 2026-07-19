# Project Instruction

## AI Agent 行为规范

### 基本原则
- 不猜测、不编造：不假设目录结构/文件/接口/字段存在。以仓库实际代码为准（Source of Truth）。文档与代码冲突时优先代码并向开发者说明。
- 优先复用已有实现：修改前先查找是否已有相同或类似实现，不重复造轮子。

### 修改流程
1. 阅读相关目录及代码 → 2. 理解已有实现及调用关系 → 3. 判断是否有可复用实现 → 4. 说明修改计划及涉及文件 → 5. 经确认后开始修改 → 6. 总结修改内容及影响范围 → 7. 等待下一步任务，不主动继续修改其他模块

### 修改原则
- **最小改动**：只改当前任务必要文件，不"顺手优化"无关代码
- **兼容性**：不修改公共接口、其他成员依赖的函数签名、已有调用关系
- **一致性**：保持项目原有代码风格/目录结构/命名规范/设计模式

### 禁止行为（未经明确授权）
- 删除大量代码、大规模重构、修改架构/目录结构/数据库/Docker/CI-CD
- 重命名大量文件或模块、修改公共接口
- 升级或替换核心依赖、引入新的第三方框架
- 危险 Git 操作：`reset --hard` / `clean -fd` / `push --force` / `rebase` / `branch -D`

### 发现问题时
不要直接修改。说明：(1)问题 (2)为什么是问题 (3)建议方案，等待确认后修改。

### 信息不足时
不要猜测或自行补全。说明还需查看哪些文件、为什么、缺失什么信息。

### 输出要求
完成开发后总结：修改了哪些文件、每个文件改了什么、修改原因、是否影响其他模块、是否需要同步修改/新增测试/其他成员配合。

### 开发目标
目标是代码正确性、多人协作兼容性、项目稳定性、可维护性、最小影响范围。多种方案时优先选稳定兼容易维护的，而非代码最少或最复杂的。

### Token Optimization

**默认：**

✓ 当前文件

✓ git diff

✓ import 文件

**禁止：**

× 全局 grep

× 全仓库 tree

× 全 docs

× 全 tests

只有任务无法完成，才允许扩大分析范围。

---

## 全局要求

### 职责边界
1. 只生成自己任务内的部分，分工之外留白并加注释：
   ```python
   # [F-01] 由 成员A 负责，待其接入 JWT 后完善
   # 预期接口: get_current_user() -> SysUser
   ```
2. `app/core/`（`database.py`/`redis.py`/`elasticsearch.py`/`security.py`/`deps.py`）由**成员F统一维护**，其他成员不得修改。需求向F提出。
3. 使用 `pyproject.toml` 未包含的库时，先通知成员F统一添加并 `uv lock`。

### 代码质量
- 类/函数须有 docstring（功能/参数/返回值），超5行逻辑加行内注释，待办用 `# TODO(成员X)`
- 数据库会话遵循项目已有生命周期管理，不得自行创建未释放连接，禁止修改已有实现
- API 响应统一使用 `app.utils.response`：
  ```python
  from app.utils.response import success, error, paginate
  return success(data=result); return error(code=400, msg="..."); return paginate(items, total, page, page_size)
  ```

## 五、文档管理

### 文档存放位置

所有说明文档统一存放在 `docs/` 目录下，各成员按需查阅。文档会持续更新，以实际文件为准。

### 协作留白

难以注释的部分生成 `docs/成员X-协作注意事项.md`，说明接口约定、待填充代码位置、预期对方接口签名（如 `async def get_current_user() -> SysUser`）。推送到远程后群内@相关人员。

### 提交前检查
```bash
python -c "compile(open('f.py').read(),'f.py','exec'); print('OK')"  # 语法检查
python -c "from app.xxx import yyy; print('OK')"                     # 导入检查
git status                                                           # 检查 staged 文件
grep -rn "TODO\|\bpass\b\|待实现\|待补充" app/                        # 检查待办
pytest                                                               # 运行测试
# 若新增依赖，确认 pyproject.toml + uv.lock 已同步
```

---

## 分支管理

### 第一阶段：初次开发（当前）

#### 分支职责

| 分支                   | 负责人 | 用途                                             |
| ---------------------- | ------ | ------------------------------------------------ |
| `main`                 | 成员F  | 稳定版本，仅存放经过测试、可发布的完整项目       |
| `develop`              | 成员F  | 集成所有成员开发成果，用于联调、测试、兼容性验证 |
| `feature/auth-A`       | 成员A  | 注册登录、用户组织模块                           |
| `feature/ai-core-B`    | 成员B  | 模型管理、技能、数字员工                         |
| `feature/im-backend-C` | 成员C  | IM 后端                                          |
| `feature/compliance-D` | 成员D  | IM 前端、合规模块                                |
| `feature/nl2sql-E`     | 成员E  | NL2SQL、沙箱                                     |
| `feature/crawler-F`    | 成员F  | 爬虫及基础设施                                   |

---

## Git 权限

### 成员A~E

允许：

- 修改自己的 Feature 分支
- Push 到自己的 Feature 分支
- 本地测试
- 提交协作文档

禁止：

- 修改 `develop`
- 修改 `main`
- Merge 到 `develop`
- Merge 到 `main`
- Rebase 公共分支

---

### 成员F

负责：

- Review 全部成员代码
- 检查兼容性
- 检查调用链
- 检查数据库影响
- 检查 API 影响
- Merge Feature → Develop
- 联调测试
- Merge Develop → Main
- 发布稳定版本

---

## AI 工作流

AI 负责：

- 阅读代码
- 修改代码
- Review
- 分析兼容性
- 查找复用实现
- 输出修改计划
- 输出 Review 结果

AI 默认允许执行：

```bash
git diff
git status
git show
git log
git branch
```

AI 默认禁止执行：

```bash
git add
git commit
git checkout
git switch
git merge
git rebase
git pull
git push
git stash
git reset
git clean
```

只有开发者明确要求时，

AI 才允许执行上述 Git 操作。

---

# 成员开发流程（A~E）

## Step 1

切换到自己的 Feature 分支。

```bash
git checkout feature/<模块>-<姓名>
```

---

## Step 2

AI 阅读：

- 当前修改文件
- import 文件
- 当前调用链

输出：

- 修改计划
- 涉及文件
- 风险分析

经开发者确认后开始修改。

---

## Step 3

开发完成。

运行：

```bash
pytest
```

或项目已有测试。

确保：

- 无语法错误
- 无导入错误
- 功能正常

---

## Step 4

人工执行 Git。

```bash
git status

git add .

git commit -m "feat(<scope>): <subject>"

git push origin feature/<模块>-<姓名>
```

---

## Step 5

通知成员F进行 Review。

开发结束。

不得自行 Merge。

---

# 成员F Review 工作流

收到成员通知后。

---

## Step 1

切换 develop。

```bash
git checkout develop

git pull origin develop
```

---

## Step 2

AI Review。

Review 范围：

1. git diff
2. 修改文件
3. import 文件
4. 当前调用链

默认禁止扫描整个仓库。

只有无法确定影响范围时，

才允许扩大分析。

---

Review 内容：

- 是否符合规范
- 是否兼容 develop
- 是否影响数据库
- 是否影响 API
- 是否影响其他成员
- 是否存在循环引用
- 是否存在重复实现

输出：

```
PASS

PASS WITH WARNING

FAIL
```

并说明：

- 风险等级
- 修改建议
- 是否允许 Merge

---

## Step 3

Review 通过。

人工执行：

```bash
git merge feature/<模块>-<姓名>
```

---

## Step 4

运行：

```bash
pytest
```

启动：

- Docker
- FastAPI
- Redis
- MySQL
- Elasticsearch

验证：

- 服务正常
- 接口正常
- 数据库正常
- 联调正常

---

## Step 5

人工：

```bash
git push origin develop
```

完成：

Feature → Develop

---

# 发布流程（成员F）

所有 Feature 已完成。

develop：

测试通过。

执行：

```bash
git checkout main

git pull origin main

git merge develop

git push origin main
```

完成：

Develop → Main

发布稳定版本。

---

# 协作文档流程

成员新增：

```
docs/成员X-协作注意事项.md
```

正常提交：

```bash
git add docs/

git commit -m "docs: 更新协作注意事项"

git push origin feature/<模块>-<姓名>
```

成员F在 Merge Feature 时，

文档随 Feature 一同进入 Develop。

不得使用：

```bash
git checkout feature/<模块>-<姓名> -- docs/
```

同步文档。

---

## 技术规范

| 类别 | 规范 |
|------|------|
| Python | 3.11+, 4空格缩进, 行宽≤100, 类PascalCase/函数snake_case/常量UPPER_SNAKE/私有_prefix_ |
| 数据库 | utf8mb4/utf8mb4_unicode_ci, 所有表含id(BIGINT PK)/created_at/updated_at/is_deleted, 外键在应用层维护 |
| API | BaseURL `/api/v1`, 统一响应 `{"code":0,"message":"ok","data":{}}` / `{"code":-1,"message":"error","data":null}` |
| 提交信息 | `<type>(<scope>): <subject>` — feat/fix/docs/refactor/chore |

---

## 六人分工

以下为职责参考，以仓库实际目录为准，AI 不得因文档存在而假设文件一定存在。

| 成员 | 模块 | 文件 |
|------|------|------|
| **A** | F-00注册登录+F-01用户组织 | `api/v1/auth.py` `api/v1/users.py` `models/user.py` `services/auth_service.py` `services/user_service.py` `schemas/user.py` |
| **B** | F-02模型+F-05技能+F-06数字员工 | `api/v1/models_config.py` `api/v1/skills.py` `api/v1/digital_employees.py` `models/model_config.py` `models/skill.py` `models/digital_employee.py` `services/model_service.py` `services/skill_service.py` `services/digital_employee_service.py` `ai/client.py` `ai/agent_executor.py` `ai/skill_generator.py` |
| **C** | F-07 IM后端 | `im/connection_manager.py` `im/message_handler.py` `im/presence.py` `api/v1/im.py` `api/v1/websocket.py` `models/im.py`(群组/消息/好友) |
| **D** | F-07 IM前端+F-08合规 | `frontend/` `api/v1/compliance.py` `services/compliance_service.py` `models/im.py`(敏感词) `models/audit_log.py` `utils/sensitive_filter.py` |
| **E** | F-03 NL2SQL+沙箱 | `api/v1/nl2sql.py` `services/nl2sql_service.py` `ai/nl2sql.py` `models/nl2sql.py` `sandbox/executor.py` `sandbox/sql_validator.py` `schemas/nl2sql.py` |
| **F** | F-04爬虫+基础设施 | `docker-compose.yml` `Dockerfile` `core/redis.py` `core/elasticsearch.py` `models/crawler.py` `schemas/crawler.py` `services/crawler_service.py` `api/v1/crawlers.py` `scheduler/crawler_scheduler.py` |

---

## `__init__.py` 导出规范

每个模块的 `__init__.py` 应导出本模块的公开组件（与已有规范保持一致）。不要为了导出而修改其他成员负责的模块。

```python
from app.models.crawler import CrawlerTask, CrawlerExecutionLog, DataCleanRule
__all__ = ["CrawlerTask", "CrawlerExecutionLog", "DataCleanRule"]
# 使用: from app.models import CrawlerTask
```
