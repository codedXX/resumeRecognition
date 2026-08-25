# AI 简历识别系统

`frontend/` 是 React + TypeScript + Vite 的招聘评估工作台；`backend/` 是 FastAPI、AgentScope、解析和评分服务。

## 本地运行

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app --reload

cd frontend
npm install
npm run dev
```

复制 `backend/.env.example` 为 `backend/.env` 后配置运行参数。默认 `EVALUATION_PROVIDER=heuristic`，仅用于本地开发和测试；设为 `agentscope` 时必须提供 `OPENAI_API_KEY`，并可通过 `OPENAI_BASE_URL` 使用兼容服务。

上传文件保存在 `UPLOAD_DIR`，不会被应用公开为静态资源；日志不得写入简历文本。`RESUME_RETENTION_DAYS` 为部署侧的保留策略配置，默认 30 天，部署前应按组织的数据保留要求设置并安排清理任务。

## 验证

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest
cd frontend && npm run build && npm test
```
