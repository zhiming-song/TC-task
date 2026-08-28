ARG NODE_IMAGE=docker.m.daocloud.io/library/node:22-alpine
ARG NGINX_IMAGE=docker.m.daocloud.io/library/nginx:1.27-alpine

FROM ${NODE_IMAGE} AS builder

WORKDIR /app
RUN npm install -g pnpm@10.14.0 --registry=https://registry.npmmirror.com
RUN pnpm config set registry https://registry.npmmirror.com

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
# 域名根路径部署：产物挂在 /，接口走同源 /api（由本容器 nginx 反代到后端）
ARG VITE_BASE_PATH=/
ARG VITE_API_BASE_URL=/api
ENV VITE_BASE_PATH=${VITE_BASE_PATH}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN pnpm build

FROM ${NGINX_IMAGE} AS runner

ENV TZ=Asia/Shanghai

COPY --from=builder /app/dist /usr/share/nginx/html
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
  listen 80;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

  # 微信群聊记录等较大请求体
  client_max_body_size 10m;

  # 后端 API：同源 /api 原样转发（后端路由本身带 /api 前缀）。
  # upstream 用变量 + Docker 内置 resolver，后端容器重建换 IP 后无需重启本容器。
  location /api/ {
    resolver 127.0.0.11 valid=10s ipv6=off;
    set $backend_upstream http://tc-agent-backend:8000;
    proxy_pass $backend_upstream;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection "";
    # SSE 流式输出（/api/chat/stream）：关闭缓冲，拉长读超时等 LLM 长回复
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
  }

  # 产品图片由后端静态资源路由提供
  location /images/ {
    resolver 127.0.0.11 valid=10s ipv6=off;
    set $backend_upstream http://tc-agent-backend:8000;
    proxy_pass $backend_upstream;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection "";
  }

  # SPA：所有路径兜底回 index.html（含 /assets 等静态资源由 try_files 优先命中）
  location / {
    try_files $uri $uri/ /index.html;
  }
}
EOF

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=3 --start-period=5s \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
