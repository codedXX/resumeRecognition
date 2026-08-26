## 1. AgentScope 异步调用修正

- [x] 1.1 修改 `AgentScopeProvider`，直接等待异步模型响应并保留结构化对象/JSON 文本的统一解析路径；用类型检查或最小 provider 测试确认不再产生未等待 coroutine
- [x] 1.2 在评估异常路径增加不含请求载荷的阶段或异常类型诊断（如确有必要），并验证 API Key、简历全文、提示词和完整模型响应不会进入日志

## 2. 回归测试

- [x] 2.1 增加异步 fake Agent 返回结构化字典的单元测试，验证结果包含合法分数、理由、满足条件、待补证据和证据引用
- [x] 2.2 增加异步 fake Agent 返回 JSON 文本/fenced JSON 的测试，并验证 malformed 响应仍按现有通用失败语义处理
- [x] 2.3 扩展批次评估测试，验证一个文件的 provider 异常被隔离、同批其他文件仍完成，并运行 `backend/.venv/Scripts/python.exe -m pytest -q`

## 3. 集成验证与交付

- [x] 3.1 使用 `RUN_BAILIAN_SMOKE=1` 和后端工作目录执行真实百炼冒烟测试，确认配置模型返回可解析的 `EvaluationResult`
- [x] 3.2 重启单 worker 后端并通过 `/health`、上传/评估流程验证前端不再显示“评分服务未返回有效结果”；同时运行 `frontend/npm test` 和 `frontend/npm run build`
- [x] 3.3 运行 `openspec validate "fix-agentscope-async-evaluation" --type change --strict --no-interactive`，确认全部提案工件通过严格校验
