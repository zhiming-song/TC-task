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

# 产物 base 为 /tc/（构建期注入），但容器自身只负责在根 / 提供静态文件。
# /tc/ 前缀由外层 nginx-gateway 的 tc-agent.conf 剥离后转发到本容器根路径。
COPY --from=builder /app/dist /usr/share/nginx/html
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
  listen 80;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

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
