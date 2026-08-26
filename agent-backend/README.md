# 程星AI智能行程助手 Backend

基于 FastAPI 的受控行程规划 Agent。通过 DeepSeek 理解群聊和用户意图，使用确定性工具完成需求校验、演示交通/酒店/门票查询、按天日程、ABC方案、均摊和投票草案，并将业务数据保存到 SQLite。

> 当前交通、酒店和门票工具处于 `demo` 模式，返回演示估价，不代表实时库存或最终成交价。

## 行程工具

- `validate_trip_requirements`：校验人数、日期、城市、房间等PRD边界并创建 `trip_id`
- `search_transport`：从 `mock_transport_inventory` 查询交通商品并写入 `transport_offers`
- `search_hotels`：从 `mock_hotel_inventory` 查询酒店商品并写入 `hotel_offers`
- `search_attractions`：从 `mock_ticket_inventory` 查询门票商品并写入 `attraction_tickets`
- `build_daily_itinerary`：生成按天日程草案和版本
- `compose_plan_options`：生成固定ABC三套方案并精确计算金额
- `calculate_equal_split`：按分等额均摊，保证个人金额之和等于总价
- `create_vote_draft`：保存投票草案
- `get_trip_data`：从SQLite读取完整行程资料

SQLite 默认位置：`data/travel_agent.db`。可通过 `SQLITE_PATH` 修改。

首次启动会自动预置12个城市的Mock商品目录：528个交通产品、108个酒店产品和48个门票产品。商品卡片均包含库存、价格和同程频道跳转链接；这些数据仅用于产品流程演示，不代表实时库存。

本项目是纯后端，不含任何页面。配套前端见同级目录 `../frontend`。

## 技术栈

| 组件 | 用途 |
| --- | --- |
| FastAPI | Web 框架，自动生成 OpenAPI 文档 |
| Uvicorn | ASGI 服务器 |
| openai (SDK) | 调用 DeepSeek 的 OpenAI 兼容接口 |
| Pydantic v2 | 请求/响应校验 |
| pydantic-settings | 从 `.env` 读取配置 |

要求 Python 3.10+（本机验证于 3.13）。

## 目录结构

```
agent-backend/
├── app/
│   ├── main.py              # FastAPI 入口，注册 CORS 与路由
│   ├── config.py            # 环境变量配置（Settings）
│   ├── schemas.py           # 请求/响应数据模型
│   ├── agent/
│   │   ├── llm.py           # DeepSeek 客户端（懒加载单例）
│   │   └── core.py          # Agent 核心逻辑，扩展点在这里
│   └── api/
│       └── routes.py        # 接口路由
├── requirements.txt
├── .env.example             # 配置模板
└── .env                     # 实际配置（已被 git 忽略）
```

## 快速开始

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate          # macOS / Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 准备配置
copy .env.example .env             # Windows
cp .env.example .env               # macOS / Linux
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 4. 启动（默认开启热重载）
python -m app.main
```

启动后：

- 服务地址：http://127.0.0.1:8000
- 交互式文档：http://127.0.0.1:8000/docs

也可以直接用 uvicorn 启动：

```bash
uvicorn app.main:app --reload --port 8000
```

## 环境变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API Key，到 https://platform.deepseek.com 申请 | 空 |
| `DEEPSEEK_BASE_URL` | 接口地址，换第三方网关时改这里 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-chat` |
| `APP_HOST` | 监听地址 | `0.0.0.0` |
| `APP_PORT` | 监听端口 | `8000` |
| `CORS_ORIGINS` | 允许的前端来源，多个用英文逗号分隔 | `http://localhost:5173` |

模型名不写死在代码里。官方当前可用的是 `deepseek-chat`（对话）和 `deepseek-reasoner`（推理），
若你走的是内部渠道或第三方网关，把 `DEEPSEEK_MODEL` 和 `DEEPSEEK_BASE_URL` 一起改掉即可。

> `.env` 含密钥，已列入 `.gitignore`，不要提交。`.env.example` 只放占位符。

## 接口说明

所有接口以 `/api` 为前缀。

### GET /api/health

健康检查，同时返回当前生效的模型名与密钥配置状态，前端用它做连通性探测。

```json
{
  "status": "ok",
  "model": "deepseek-chat",
  "api_key_configured": true
}
```

### POST /api/chat

一次性返回完整回复，适合脚本调用或不需要打字机效果的场景。

请求：

```json
{
  "messages": [
    { "role": "user", "content": "你好" }
  ],
  "temperature": 0.7
}
```

- `messages`：对话历史，按时间顺序，至少 1 条。`role` 取 `system` / `user` / `assistant`
- `temperature`：可选，范围 0.0 ~ 2.0，默认 0.7

响应：

```json
{
  "reply": "你好！有什么可以帮你的？",
  "model": "deepseek-chat"
}
```

### POST /api/chat/stream

参数与 `/api/chat` 完全一致，以 SSE（`text/event-stream`）逐字返回，供前端做流式输出。

```
data: {"token": "你"}

data: {"token": "好"}

data: [DONE]
```

出错时会先推一条错误事件，再推 `[DONE]`：

```
data: {"error": "调用模型失败: ..."}

data: [DONE]
```

### 错误约定

非流式接口调用模型失败时返回 `502`：

```json
{ "detail": "调用模型失败: <原因>" }
```

请求体不合法由 FastAPI 返回 `422`。

## 调试

```bash
# 健康检查
curl http://127.0.0.1:8000/api/health

# 对话
curl -X POST http://127.0.0.1:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}]}"
```

或者直接打开 `/docs` 在页面上点。

## 扩展方向

- **Agent 能力**：`app/agent/core.py` 的 `Agent` 类是核心。工具调用（function calling）、
  检索增强、长期记忆都在这里加。`chat` 与 `chat_stream` 是两个入口
- **系统提示词**：改 `core.py` 里的 `DEFAULT_SYSTEM_PROMPT`，或在构造 `Agent` 时传入
- **会话管理**：目前多轮上下文由前端携带，服务端无状态。若要服务端管理会话，
  在 `app/api/routes.py` 增加 session 存储（内存字典 / Redis）
- **多 Agent**：`Agent` 支持传入不同 model 与 system_prompt，可实例化多个用于不同场景
