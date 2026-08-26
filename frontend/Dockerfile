ARG NODE_IMAGE=docker.m.daocloud.io/library/node:22-alpine
ARG NGINX_IMAGE=docker.m.daocloud.io/library/nginx:1.27-alpine

FROM ${NODE_IMAGE} AS builder

WORKDIR /app
RUN npm install -g pnpm@10.14.0 --registry=https://registry.npmmirror.com
RUN pnpm config set registry https://registry.npmmirror.com

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
ARG VITE_BASE_PATH=/tc/
ARG VITE_API_BASE_URL=/tc/api
ENV VITE_BASE_PATH=${VITE_BASE_PATH}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN pnpm build

FROM ${NGINX_IMAGE} AS runner

ENV TZ=Asia/Shanghai

# 产物 base 为 /tc/，因此放到 html/tc 下，使 /tc/assets/... 能直接命中
COPY --from=builder /app/dist /usr/share/nginx/html/tc
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
  listen 80;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

  # API 反代到后端容器；SSE 流式必须关闭缓冲
  location /tc/api/ {
    proxy_pass http://tc-agent-backend:8000/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    chunked_transfer_encoding off;
  }

  # 前端 SPA，兜底回 /tc/index.html
  location /tc/ {
    try_files $uri $uri/ /tc/index.html;
  }

  location = / {
    return 302 /tc/;
  }
}
EOF

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=3 --start-period=5s \
  CMD wget -qO- http://127.0.0.1/tc/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
