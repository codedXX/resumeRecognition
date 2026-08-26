# Ubuntu 24.04 安装 Docker、配置镜像加速与拉取镜像

适用环境：阿里云 ECS、Ubuntu 24.04 64 位、新服务器。

## 1. 更新系统

登录服务器后执行：

```bash
sudo apt update
sudo apt install -y ca-certificates curl
```

## 2. 安装 Docker

依次执行：

```bash
sudo install -m 0755 -d /etc/apt/keyrings
```

```bash
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
```

```bash
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

```bash
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

## 3. 验证 Docker 已安装

```bash
sudo docker run hello-world
```

终端出现 `Hello from Docker!` 就表示 Docker 安装成功。

## 4. 先测试是否能直接拉取镜像

```bash
sudo docker pull nginx:stable
```

如果速度正常且没有报错，不需要配置镜像加速器，直接使用 Docker 即可。

如果拉取很慢、超时或失败，再进行下一步。

## 5. 配置阿里云镜像加速器（可选）

在阿里云控制台打开：

```text
容器镜像服务 ACR → 镜像工具 → 镜像加速器
```

复制页面中为你的账号生成的镜像加速器地址，例如：

```text
https://你的账号地址.mirror.aliyuncs.com
```

然后执行下面命令。**必须把示例地址替换成你自己的地址。**

```bash
sudo mkdir -p /etc/docker
```

```bash
sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://替换成你自己的加速器地址"
  ]
}
EOF
```

重启 Docker：

```bash
sudo systemctl restart docker
```

确认加速器已生效：

```bash
sudo docker info
```

在输出中查找 `Registry Mirrors`。不要使用网上随意找到的公共加速器地址。

## 6. 拉取镜像

镜像加速器配置完成后，或第 4 步已直接拉取成功后，使用以下方式拉取镜像：

```bash
sudo docker pull nginx:stable
```

```bash
sudo docker pull python:3.12-slim
```

查看已经下载的镜像：

```bash
sudo docker images
```

## 常见问题

- `TLS handshake timeout` 或下载超时：检查服务器能否访问公网，并配置第 5 步中的阿里云账号专属镜像加速器。
- `unauthorized`：拉取的是私有镜像仓库，需要先执行 `docker login`。
- `manifest unknown`：镜像名或标签写错。
- 修改 `daemon.json` 后 Docker 无法启动：通常是 JSON 格式错误；删除或修正该文件后执行 `sudo systemctl restart docker`。

> 镜像加速器仅用于加速 Docker Hub 镜像拉取；它不是 Docker 安装源，也不能替代私有镜像仓库。正式部署自己的应用时，建议把应用镜像推送到阿里云 ACR，再从 ACR 拉取。
