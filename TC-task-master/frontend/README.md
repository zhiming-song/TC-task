# Agent Frontend

Vue 3 + Vite 编写的对话页面，通过 HTTP API 调用 Agent 后端。

本项目是纯前端，不含任何模型逻辑，所有能力来自后端接口。配套后端见同级目录 `../agent-backend`。

## 技术栈

| 组件 | 用途 |
| --- | --- |
| Vue 3 | 组合式 API（`<script setup>`） |
| Vite 6 | 开发服务器与构建 |
| 原生 fetch | 接口调用，未引入 axios |

要求 Node.js 18+。

## 目录结构

```
frontend/
├── index.html
├── vite.config.js                  # 开发服务器与 /api 代理
├── package.json
└── src/
    ├── main.js                     # 应用入口
    ├── App.vue                     # 整体布局、后端状态检测
    ├── style.css                   # 全局样式与 CSS 变量
    ├── api/
    │   └── agent.js                # 接口封装（含 SSE 流式解析）
    └── components/
        └── ChatBox.vue             # 聊天界面
```

## 快速开始

先确认后端已在 `127.0.0.1:8000` 跑起来（见 `../agent-backend/README.md`），然后：

本项目使用 **pnpm** 管理依赖（仓库带 `pnpm-lock.yaml`）。

```bash
pnpm install
pnpm dev
```

打开 http://localhost:5173 。

若只用 npm，请先删除 `pnpm-lock.yaml` 再 `npm install`（否则 npm 会解析失败）。

## 可用脚本

| 命令 | 说明 |
| --- | --- |
| `pnpm dev` | 启动开发服务器，端口 5173 |
| `pnpm build` | 构建产物输出到 `dist/` |
| `pnpm preview` | 本地预览构建产物 |

## 接口对接

`src/api/agent.js` 封装了三个方法，统一以 `/api` 为前缀：

| 方法 | 对应接口 | 说明 |
| --- | --- | --- |
| `fetchHealth()` | `GET /api/health` | 探测后端连通性，取当前模型名 |
| `chat(messages, temperature)` | `POST /api/chat` | 一次性返回完整回复 |
| `chatStream(messages, onToken, temperature)` | `POST /api/chat/stream` | 流式，逐字回调 |

`messages` 格式与后端一致：

```js
[
  { role: 'user', content: '你好' },
  { role: 'assistant', content: '你好！有什么可以帮你的？' },
]
```

页面默认走 `chatStream`。它内部用 `ReadableStream` 读取 SSE，按 `\n\n` 切分事件，
解析 `data:` 后的 JSON 并逐个 token 回调，遇到 `[DONE]` 结束。

多轮上下文由前端维护并在每次请求时完整携带，后端无状态。

## 跨域与代理

开发环境通过 `vite.config.js` 的 proxy 把 `/api` 转发到后端，不存在跨域问题：

```js
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}
```

后端端口有变动就改这里的 `target`。

生产部署：`npm run build` 后把 `dist/` 交给 Nginx 托管，并在 Nginx 上做 `/api` 反向代理指向后端。
注意 SSE 需要关闭缓冲：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_buffering off;
    proxy_cache off;
}
```

若不走代理而是直连后端域名，记得把前端地址加进后端的 `CORS_ORIGINS`。

## 交互说明

- `Enter` 发送，`Shift + Enter` 换行
- 回复流式逐字输出，生成期间输入框与按钮禁用
- 顶部圆点显示后端连通状态与当前模型名
- 「清空」按钮重置对话历史

## 扩展方向

- **Markdown 渲染**：当前用 `white-space: pre-wrap` 纯文本展示，需要富文本可引入
  `markdown-it` + `highlight.js`，注意做 XSS 过滤
- **会话列表**：多会话切换可在 `App.vue` 增加侧边栏，配合 `localStorage` 持久化
- **中断生成**：`chatStream` 可接收 `AbortSignal`，配合按钮实现停止生成
- **状态管理**：目前状态在组件内，规模变大再引入 Pinia

## 移动端（H5）适配

页面已做响应式处理，手机浏览器打开即表现为类 App 的全屏聊天界面：

- `index.html` 设置 `viewport-fit=cover`、禁用用户缩放，并声明 `apple-mobile-web-app-capable`
- 视口高度用 `100dvh`（动态视口），避开移动端浏览器地址栏伸缩
- 媒体查询 `(max-width: 768px)`：去掉桌面端的居中卡片边框与内边距，`.shell` 铺满全屏；头部更紧凑、隐藏副标题
- 输入框字号 `16px`，避免 iOS 聚焦时自动放大；`composer` 底部叠加 `env(safe-area-inset-bottom)`，适配全面屏底部安全区
- 顶部 header 叠加 `env(safe-area-inset-top)`，避开刘海 / 状态栏

桌面端（>768px）仍保持居中的卡片式外观，两种布局共用同一套组件。

