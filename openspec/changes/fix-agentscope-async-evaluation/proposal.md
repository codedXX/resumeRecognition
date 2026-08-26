## Why

启用阿里云百炼后，简历评估会稳定失败，并在前端显示“评分服务未返回有效结果”。根因是当前 AgentScope 版本的 `Agent.reply()` 为异步方法，但适配器把它提交到线程池后没有等待真正的响应；现在已有真实冒烟测试证明凭据、模型和结构化输出接口本身可用，应立即修正调用链，恢复百炼评估能力。

## What Changes

- 修正 AgentScope 评估适配器对异步 `Agent.reply()` 的调用方式，确保等待真实 `Msg` 响应。
- 保留对 `structured_output` 字典和文本 JSON 回退的现有校验路径。
- 增加回归测试，覆盖异步 AgentScope 响应、结构化字典解析和单文件评估成功路径。
- 保留现有单文件失败隔离和前端错误展示语义；不改变评分阈值或岗位规则合同。

## Capabilities

### New Capabilities

- `bailian-evaluation-runtime`: 保证已配置的百炼/AgentScope 评估请求被正确等待、解析并产出有效评分结果。

### Modified Capabilities

无。

## Impact

- 影响 `backend/app/evaluation.py` 的 AgentScope 调用适配器及其后端评估测试。
- 不新增依赖，不改变 HTTP API 响应结构或前端代码。
- 真实百炼联网冒烟测试仍由显式环境变量控制；离线测试默认不访问外部服务。
