# 部署说明（www.tankpizza.cn 根域名）

本栈已从「`/tc/` 子路径 + 网关改写」改造为「域名根路径直接访问」：

```
浏览器 https://www.tankpizza.cn/
        │
        ▼
tc-agent-gateway（Nginx，TLS 终结）
        │  proxy_pass → http://tc-agent-frontend:80（docker 网络 gateway）
        ▼
tc-agent-frontend（nginx：静态 SPA + /api 同源反代）
        │  location /api/ → http://tc-agent-backend:8000（docker 网络 tc-agent-internal）
        ▼
tc-agent-backend（FastAPI，路由前缀 /api，仅内网可达）
```

要点：
- 前端构建期注入 `VITE_BASE_PATH=/`、`VITE_API_BASE_URL=/api`，接口与页面同源，天然无跨域。
- SSE 流式（`/api/chat/stream`）在前端容器与网关两侧都关闭了 `proxy_buffering`，逐字输出不攒包。
- 后端不再挂 `gateway` 网络，只能经前端容器访问，减少暴露面。

## 部署步骤

```bash
# 1. 服务器上拉取代码
git pull

# 2. 确认 agent-backend/.env 存在（DEEPSEEK_API_KEY 等，见 .env.example）

# 3. 构建并启动
docker compose up -d --build

# 4. 验证
curl -s https://www.tankpizza.cn/api/health     # {"model":"deepseek-chat",...}
curl -sI https://www.tankpizza.cn/ | head -1    # HTTP/1.1 200
curl -sI http://tankpizza.cn/ | head -1         # 301 → https://www.tankpizza.cn/
```

## 网关与证书

Compose 会启动 `tc-agent-gateway`，并挂载 `deploy/tankpizza-gateway.conf`。
默认从宿主机 `/etc/letsencrypt` 只读挂载证书；如证书目录不同，可设置
`LETSENCRYPT_DIR` 后再执行 Compose 命令。

若之前从未在网关接入 `tankpizza.cn` 证书：

```bash
certbot certonly --nginx -d tankpizza.cn -d www.tankpizza.cn
```

## 本地开发（不受影响）

- 后端：`uvicorn app.main:app --port 8000`
- 前端：`pnpm dev`（vite 5173，`/api` 由 vite proxy 转发到 8000，无需 CORS）
