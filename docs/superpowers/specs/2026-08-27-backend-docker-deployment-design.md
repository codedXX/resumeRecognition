# 后端 Docker 部署设计

## 目标

将 FastAPI 后端打包为可在服务器运行的 Docker 镜像，并使用现有的 Docker Compose 配置部署。

## 已确认的服务器目录

部署目录为 `/opt/resumeRecognition/backend`，其中包含 `data/`、`.env.production` 和 `compose.yml`。所有 Compose 命令均从该目录运行。

## 方案

- 在 `backend/Dockerfile` 中使用 Python 3.12 slim 基础镜像并安装 `requirements.txt` 中的运行时依赖。应用使用 Docker 默认用户运行，以确保可写入宿主机挂载的 `data/` 目录。
- 容器工作目录设为 `/app`，启动命令固定为单 worker 的 Uvicorn：`app.main:app --host 0.0.0.0 --port 8000 --workers 1`。
- `backend/compose.yml` 使用由 `docker load` 导入的本地镜像 `resume-backend:local`，保留端口 `8000:8000` 与重启策略；Dockerfile 仅在本地打包镜像时使用。
- Compose 将 `./data` 挂载为容器 `/data`，并通过 `ROLES_FILE=/data/roles.json` 使岗位规则在容器重建或服务重启后保留。
- `.env.production` 仅由 Compose 在运行时加载，不能复制进镜像；`.dockerignore` 还会排除虚拟环境、缓存和测试产物。

## 运行与验证

在 `/opt/resumeRecognition/backend` 执行 `docker compose up -d --build`。服务健康检查可通过 `http://服务器地址:8000/health` 验证；返回 `{"status":"ok"}` 表示 API 已启动。

## 非目标

本次不容器化前端，也不引入多副本或多 worker，因为当前批次分析状态保存在单个进程内存中。
