# AI 简历识别系统

`frontend/` 是 React + TypeScript + Vite 的招聘评估工作台，`backend/` 是 FastAPI 简历解析与评分服务。

## 本地运行

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app --workers 1

cd frontend
npm install
npm run dev
```

复制 `backend/.env.example` 为 `backend/.env`。岗位规则保存在后端 `ROLES_FILE` 指定的 JSON 文件中，默认是 `backend/data/roles.json`；应用会以临时文件替换方式写入，并使用锁避免多个进程同时修改。

简历二进制和提取文本只存在于当前进程内存，评分结束、失败或待处理批次过期后会清理文本。评分结果和证据 Diff 也只保留在当前进程；重启服务会清空分析结果，但不会清空岗位规则。系统面向少量内部用户，必须使用单 worker，不能使用多个 worker 或多副本共享同一运行时。

## 阿里百炼

默认 `EVALUATION_PROVIDER=heuristic` 仅用于开发和测试。生产环境可设置：

```dotenv
EVALUATION_PROVIDER=bailian
OPENAI_API_KEY=你的百炼兼容 API Key
OPENAI_MODEL=qwen-plus
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

后端通过 AgentScope 的 OpenAI 兼容接口调用百炼，并要求模型返回结构化评分；若服务返回 JSON 文本，系统会进行严格 JSON/Pydantic 校验。API Key 只放在后端环境变量中，日志不得写入简历全文、提示词或完整模型响应。

## 验证

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest
cd frontend && npm run build && npm test
```

