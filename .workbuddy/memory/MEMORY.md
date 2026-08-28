# TC-task-master 项目备忘

## 项目概要
程星AI智能行程助手：FastAPI 受控行程规划 Agent（DeepSeek）+ Vue3/Vite 聊天前端。docker-compose 依赖外部 gateway 网络（本机无 docker，走本地启动）。

## 本地启动方式（验证可用）
- 后端（8000）：`/Users/user/Desktop/TC-task-master/agent-backend/.venv/bin/uvicorn app.main:app --app-dir /Users/user/Desktop/TC-task-master/agent-backend --host 0.0.0.0 --port 8000`
- 前端（5173）：`/Users/user/.workbuddy/binaries/node/versions/22.22.2/bin/node /Users/user/Desktop/TC-task-master/frontend/node_modules/vite/bin/vite.js serve /Users/user/Desktop/TC-task-master/frontend --port 5173 --strictPort`
- 坑1：Bash 每次调用工作目录重置到项目根，`python -m app.main` 必须在 agent-backend 下执行 → 用 `--app-dir` 绕开。
- 坑2：pnpm 未安装，用 `npx pnpm --dir <frontend> install`；esbuild 构建脚本被 pnpm 安全策略忽略导致 exit 1，但平台二进制在位不影响运行；`pnpm dev` 会因预检失败，直接用 node 跑 vite.js。
- `.env` 在 agent-backend/ 下（含 DEEPSEEK_API_KEY，git 忽略）；config.py 用绝对路径读 .env，与 cwd 无关。

## 用户（Zoey）
同程旅行酒店业务产品经理，正在做「AI 对比 RP（房型）」功能。
