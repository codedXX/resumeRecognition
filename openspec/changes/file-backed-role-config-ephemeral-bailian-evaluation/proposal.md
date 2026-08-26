## Why

当前系统为岗位规则、分析批次和评分结果引入了 SQLite，但产品只面向两三名用户，且已明确不需要历史记录、刷新恢复或长期保存分析结果。与此同时，生产评分需要接入阿里云百炼；现在的 AgentScope 适配器已经具备 OpenAI 兼容接口基础，可以在移除数据库的同时完成一次轻量、可配置的百炼接入。

## What Changes

- **BREAKING** 移除 SQLite/SQLAlchemy/Alembic 作为运行时持久化层；当前分析批次、临时解析文本、评分结果和证据 Diff 全部保存在单个 FastAPI 进程内存中，进程重启后清空。
- 将岗位规则迁移到后端可写的 `backend/data/roles.json`，继续通过现有岗位 CRUD API 管理，不把运行时数据放入前端 `public` 静态目录。
- 为岗位文件增加 JSON 校验、稳定 ID、原子替换写入和最小必要的并发写保护，避免保存过程中损坏配置。
- 保持上传文件只在请求和当前分析内存中解析，不落盘；分析完成后不建立长期结果历史。
- 通过现有 AgentScope 的 OpenAI 兼容模型适配器接入阿里云百炼，API Key、模型名、地域/业务空间 Base URL 全部从后端环境变量读取。
- 要求百炼返回可验证的结构化评分结果；在模型不支持直接 schema 输出时，使用 JSON 输出加 Pydantic 校验，并将无效响应视为单文件评分失败。
- 在文档和界面中明确提示：分析文本会发送到阿里云百炼，评分结果仅在当前进程内短暂存在。
- **BREAKING** 服务需以单 worker 运行；不承诺多进程共享当前分析状态、服务重启恢复或历史审计能力。

## Capabilities

### New Capabilities

- `file-backed-role-rules`: 定义岗位规则 JSON 文件的读取、创建、更新、删除、排序、校验和安全写入行为。
- `ephemeral-screening-runtime`: 定义无数据库的内存批次、上传解析、异步评估、结果查询和进程生命周期行为。
- `bailian-evaluation-provider`: 定义通过 AgentScope/OpenAI 兼容接口调用阿里云百炼、结构化评分输出、配置管理和失败处理行为。

### Modified Capabilities

无。项目当前没有可同步的主规格目录，本次以三个独立的新能力记录运行时契约。

## Impact

- 主要影响 `backend/app/main.py`、`backend/app/models.py`、`backend/app/database.py`、`backend/app/evaluation.py`、`backend/app/config.py`、后端测试和运行文档。
- 可能移除 SQLAlchemy、Alembic 及数据库配置；前端岗位 API 合同尽量保持不变。
- 新增后端 `data/roles.json` 及其初始化/写入逻辑；该文件不应包含简历文本或评分结果。
- AgentScope 依赖继续复用，新增或调整百炼环境变量和真实模型冒烟测试；API Key 不进入前端、源码或日志。
- 现有数据库中的岗位规则不会自动继续作为运行时来源；实施前需确认是否需要一次性导出为 JSON。当前分析数据和结果不提供迁移，因为新运行时按设计不保留历史。
