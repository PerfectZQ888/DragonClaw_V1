# DragonClaw Dashboard API 契约文档

> **文档版本：** v1.0  
> **生成时间：** 2026-04-12  
> **Base URL：** `http://localhost:8888`

---

## 认证方式

所有 API 端点均需通过 **Token 认证**。

**参数方式：**
```
GET /api/status?token=<AUTH_TOKEN>
```

**Token 获取：**
- 首次启动时自动生成，输出在服务端日志中
- 或通过 `GET /api/generate-token` 获取新 Token

---

## 端点清单

| 端点 | 用途 | 认证 |
|------|------|------|
| `GET /api/status` | 综合主页数据（所有监控数据的统一入口） | Token |
| `GET /api/coordination` | 协作事件数据 | Token |
| `GET /api/events` | SSE 实时事件流 | Token |

> **说明：** `/api/state`、`/api/live`、`/api/documents`、`/api/tasks`、`/api/usage` 并非独立端点，其数据均包含在 `/api/status` 返回的 `last_data` 对象中，作为子结构访问。

---

## 1. GET /api/status

综合主页数据端点，返回所有监控数据的统一 JSON 响应。

### 请求

```
GET /api/status?token=<AUTH_TOKEN>
```

### 响应体 Schema

```json
{
  "status": "string",
  "task_monitor": {
    "total_tasks": "number",
    "pending_tasks": "number",
    "running_tasks": "number",
    "completed_tasks": "number",
    "last_detect_time": "string"
  },
  "agents": "array",
  "tasks": "array",
  "skills": "object",
  "usage": "object",
  "summary": "object",
  "collaboration": "object",
  "documents": "object",
  "memories": "object",
  "risks": "array",
  "file_changes": "array",
  "system": "object",
  "connections": "object",
  "last_update": "string",
  "models": "array"
}
```

### 字段详细说明

#### `status` — 系统状态
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 必填 | 系统状态：`healthy` / `init` |

#### `task_monitor` — 任务监控摘要
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| total_tasks | number | 必填 | 任务总数 |
| pending_tasks | number | 必填 | 待处理任务数 |
| running_tasks | number | 必填 | 运行中任务数 |
| completed_tasks | number | 必填 | 已完成任务数 |
| last_detect_time | string | 必填 | 最后检测时间，格式 `YYYY-MM-DD HH:mm` 或 `HH:mm` |

#### `agents` — Agent 列表
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 必填 | Agent 显示名称 |
| name_key | string | 必填 | Agent 唯一标识键 |
| status | string | 必填 | 运行状态：`idle` / `active` / `busy` |
| config | object | 必填 | 配置信息，含 `icon`、`label`、`role` |
| tasks | number | 必填 | 当前任务数 |
| sessions | number | 必填 | 会话数 |
| model | string | 必填 | 当前使用模型名称 |

#### `tasks` — 任务列表
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | string | 必填 | 任务 ID |
| title | string | 必填 | 任务标题（最多 300 字符） |
| agent | string | 必填 | 负责的 Agent |
| status | string | 必填 | 状态：`pending` / `running` / `progress` / `done` / `completed` / `failed` |
| priority | string | 必填 | 优先级：`low` / `medium` / `high` |
| time | string | 必填 | 任务时间，格式 `YYYY-MM-DD HH:mm` 或 `HH:mm` |
| source | string | 必填 | 数据来源，固定为 `task_watcher` |

#### `skills` — 技能状态
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| ready | number | 必填 | 已就绪技能数量 |
| missing | number | 必填 | 缺失技能数量 |
| skills | array | 必填 | 技能列表（最多 50 条），每项含 `name`、`status` |

#### `usage` — 用量统计
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| requests_today | number | 必填 | 今日 API 请求次数 |
| messages_today | number | 必填 | 今日消息数 |
| input_tokens_today | number | 必填 | 今日输入 Token 数 |
| output_tokens_today | number | 必填 | 今日输出 Token 数 |
| cache_read_today | number | 必填 | 今日缓存读取 Token 数 |
| cache_write_today | number | 必填 | 今日缓存写入 Token 数 |
| cost_estimate | number | 必填 | 预估费用（美元） |
| cache_hit_rate | number | 必填 | 缓存命中率 |
| tokens_today | number | 必填 | 今日总 Token 数 |
| uptime | string | 必填 | Dashboard 运行时间，格式 `Xh Xm` / `Xd Xh Xm` |
| connections | object | 必填 | 连接状态，含 `feishu`、`gateway` |
| subscription | object | 必填 | 订阅信息，含 `plan`、`quota_info`、`reset_date` |
| limits | object | 必填 | 配额限制信息 |
| token_consumers | array | 必填 | Token 消费明细列表 |
| today_stats | object | 必填 | 今日统计汇总 |
| model_stats | object | 必填 | 各模型用量统计（key 为模型名） |
| recent_activities | array | 必填 | 最近活动列表（最多 100 条） |

#### `summary` — 综合摘要
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| system_status | string | 必填 | 系统状态：`healthy` |
| active_agents | number | 必填 | 活跃 Agent 数 |
| running_tasks | number | 必填 | 运行中任务数 |
| completed_tasks | number | 必填 | 已完成任务数 |
| failed_tasks | number | 必填 | 失败任务数 |
| total_tasks | number | 必填 | 任务总数 |
| total_sessions | number | 必填 | 会话总数 |
| active_sessions | number | 必填 | 活跃会话数 |
| uptime_hours | number | 必填 | Dashboard 运行小时数 |
| system_uptime_hours | number | 必填 | 系统运行小时数 |

#### `collaboration` — 协作数据
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| sessions | array | 必填 | 活跃会话列表，每项含 `id`、`agent`、`label`、`channel`、`status`、`messages`、`updated` |
| messages | array | 必填 | ⚠️ **始终为空数组**，硬编码未实现 |
| task_chains | array | 必填 | 任务链（扁平数组，非嵌套树结构） |
| agent_participation | object | 必填 | Agent 参与统计（key 为 agent名） |
| recent_activities | array | 必填 | 最近活动（与 `usage.recent_activities` 相同） |

#### `documents` — 文档数据
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| files | array | 必填 | 文档列表（最近 30 天内修改，最多 200 条） |
| memories | array | 必填 | 记忆文件列表（最多 50 条） |

**`documents.files` 子字段：**
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 必填 | 文件名 |
| path | string | 必填 | 文件完整路径 |
| modified | string | 必填 | 修改日期，格式 `YYYY-MM-DD` |
| size | number | 必填 | 文件大小（字节） |
| category | string | 必填 | 分类：`DBA文档` / `团队文档` / `技能文档` / `Markdown` |
| is_recent | boolean | 必填 | 是否今日更新 |

**`documents.memories` 子字段：**
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 必填 | 文件名 |
| path | string | 必填 | 文件完整路径 |
| modified | string | 必填 | 修改日期，格式 `YYYY-MM-DD` |
| size | number | 必填 | 文件大小（字节） |
| type | string | 必填 | 类型，固定为 `记忆文件` |
| status | string | 必填 | 状态：`recent` / `normal` |
| status_text | string | 必填 | 状态文本：`今日更新` / `正常` |

#### `system` — 系统信息
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| uptime_seconds | number | 必填 | 系统运行秒数（Unix timestamp） |
| uptime_hours | number | 必填 | 系统运行小时数 |
| uptime | string | 必填 | 格式化运行时间 |
| load | array | 必填 | 系统负载 `[1min, 5min, 15min]` |
| cpu_percent | number | 必填 | CPU 使用率（%） |
| memory | object | 必填 | 内存信息，含 `total`、`used`、`available`、`percent` |
| disk | array | 必填 | 磁盘信息列表，每项含 `path`、`total`、`used`、`free`、`percent` |

#### `connections` — 连接状态
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| feishu | string | 必填 | 飞书连接状态：`connected` / `disconnected` / `configured` / `unknown` |
| gateway | string | 必填 | Gateway 状态：`running` / `stopped` / `unknown` |

#### `models` — 模型配置列表
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 必填 | 模型显示名称 |
| model_id | string | 必填 | 模型 ID |
| provider | string | 必填 | 提供商名称 |
| type | string | 必填 | 类型：`primary` / `backup` |
| is_free | boolean | 必填 | 是否免费模型 |
| expire_info | string | 必填 | 过期信息（付费模型有值） |
| quota_used | number | 必填 | 已用配额 |
| quota_total | number | 必填 | 配额上限（`null` 表示无限制） |
| quota_percent | number | 必填 | 配额使用百分比 |
| calls | number | 必填 | 调用次数 |

### 响应示例

```json
{
  "status": "healthy",
  "task_monitor": {
    "total_tasks": 12,
    "pending_tasks": 3,
    "running_tasks": 2,
    "completed_tasks": 7,
    "last_detect_time": "2026-04-12 11:30"
  },
  "agents": [
    {
      "name": "帝钳统帅",
      "name_key": "main",
      "status": "active",
      "config": {"icon": "🦞", "label": "帝钳统帅", "role": "调度中枢"},
      "tasks": 2,
      "sessions": 5,
      "model": "glm-4.7-flash"
    }
  ],
  "tasks": [
    {
      "id": "task-001",
      "title": "分析系统监控数据",
      "agent": "main",
      "status": "running",
      "priority": "high",
      "time": "2026-04-12 11:25",
      "source": "task_watcher"
    }
  ],
  "skills": {
    "ready": 8,
    "missing": 2,
    "skills": [
      {"name": "agent-memory", "status": "ready"},
      {"name": "notion", "status": "ready"}
    ]
  },
  "usage": {
    "requests_today": 156,
    "messages_today": 42,
    "input_tokens_today": 78500,
    "output_tokens_today": 23400,
    "cache_read_today": 12000,
    "cache_write_today": 8500,
    "cost_estimate": 0.35,
    "cache_hit_rate": 0.15,
    "tokens_today": 101900,
    "uptime": "2h 15m",
    "connections": {"feishu": "connected", "gateway": "running"},
    "subscription": {"plan": "minimax", "quota_info": "已配置", "reset_date": "每月重置"},
    "limits": {
      "requests": {"used": 0, "limit": null, "percent": 0, "type": "unknown", "reset": "N/A"},
      "tokens": {"used": 0, "limit": null, "percent": 0, "type": "monthly", "reset": "每月重置"}
    },
    "token_consumers": [
      {"model": "minimax/MiniMax-M2.7-highspeed", "provider": "minimax", "total_tokens": 45000, "input_tokens": 45000, "output_tokens": 0, "cache_read": 0, "count": 28}
    ],
    "today_stats": {
      "input_tokens": 78500,
      "output_tokens": 23400,
      "cache_read": 12000,
      "total_tokens": 101900,
      "request_count": 156
    },
    "model_stats": {
      "minimax/MiniMax-M2.7-highspeed": {"calls": 28, "tokens": 45000, "cost": 0.15}
    },
    "recent_activities": [
      {"time": "04-12 11:30", "type": "message", "content": "分析今天的系统运行报告", "agent": "main"}
    ]
  },
  "summary": {
    "system_status": "healthy",
    "active_agents": 4,
    "running_tasks": 2,
    "completed_tasks": 7,
    "failed_tasks": 0,
    "total_tasks": 12,
    "total_sessions": 8,
    "active_sessions": 3,
    "uptime_hours": 2.3,
    "system_uptime_hours": 48.5
  },
  "collaboration": {
    "sessions": [
      {"id": "abc123", "agent": "main", "label": "main", "channel": "qqbot", "status": "active", "messages": 0, "updated": "11:30"}
    ],
    "messages": [],
    "task_chains": [],
    "agent_participation": {
      "main": {"events": 5, "tokens": 12000, "tasks": 3}
    },
    "recent_activities": []
  },
  "documents": {
    "files": [
      {"name": "API指南.md", "path": "/data/docs/API指南.md", "modified": "2026-04-12", "size": 4096, "category": "团队文档", "is_recent": true}
    ],
    "memories": [
      {"name": "2026-04-12.md", "path": "/root/.openclaw/workspace/memory/2026-04-12.md", "modified": "2026-04-12", "size": 2048, "type": "记忆文件", "status": "recent", "status_text": "今日更新"}
    ]
  },
  "memories": {
    "recent": ["2026-04-12.md", "2026-04-11.md"],
    "total": 15
  },
  "risks": [],
  "file_changes": [],
  "system": {
    "uptime_seconds": 174600,
    "uptime_hours": 48.5,
    "uptime": "2d 0h 30m",
    "load": [0.35, 0.28, 0.22],
    "cpu_percent": 12.5,
    "memory": {"total": 8388608, "used": 5242880, "available": 3145728, "percent": 62.5},
    "disk": [
      {"path": "/", "total": 50000000000, "used": 35000000000, "free": 15000000000, "percent": 70.0}
    ]
  },
  "connections": {"feishu": "connected", "gateway": "running"},
  "last_update": "2026-04-12T11:43:00.123456",
  "models": [
    {"name": "MiniMax-M2.7-highspeed", "model_id": "minimax/MiniMax-M2.7-highspeed", "provider": "minimax", "type": "primary", "is_free": false, "expire_info": "", "quota_used": 45000, "quota_total": null, "quota_percent": 0, "calls": 28}
  ]
}
```

---

## 2. GET /api/coordination

获取 Agent 协作事件数据。

### 请求

```
GET /api/coordination?token=<AUTH_TOKEN>
```

### 响应体 Schema

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 必填 | 状态，`ok` |
| total | number | 必填 | 事件总数 |
| spawn_count | number | 必填 | Spawn 事件数 |
| delegate_count | number | 必填 | Delegate 事件数 |
| tasks | array | 必填 | 事件列表（最多 50 条） |
| last_update | string | 必填 | 最后更新时间，ISO 格式 |

### 响应示例

```json
{
  "status": "ok",
  "total": 23,
  "spawn_count": 15,
  "delegate_count": 8,
  "tasks": [
    {
      "id": "coord-001",
      "type": "spawn",
      "agent": "research",
      "tokens": 3200,
      "time": "2026-04-12 11:20"
    },
    {
      "id": "coord-002",
      "type": "delegate",
      "agent": "main",
      "tokens": 1500,
      "time": "2026-04-12 11:15"
    }
  ],
  "last_update": "2026-04-12T11:43:00.123456"
}
```

---

## 3. GET /api/events

SSE（Server-Sent Events）实时事件流，持续推送最新的 `last_data` 完整对象。

### 请求

```
GET /api/events?token=<AUTH_TOKEN>
```

### 响应格式

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### 事件格式

```
data: {"status": "healthy", "agents": [...], ...}

data: {"status": "healthy", "agents": [...], ...}
```

每 30 秒发送一次 keepalive：
```
: keepalive
```

### 使用示例

```javascript
const eventSource = new EventSource('/api/events?token=' + authToken);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received update:', data.status);
};
```

---

## 注意事项（Known Issues）

### 1. `messages` 字段始终为空数组
**位置：** `collaboration.messages`  
**问题：** 该字段在代码中被硬编码为空数组 `[]`，从未被赋值。  
**影响：** 前端无法通过 API 获取协作消息历史。  
**状态：** ⚠️ 待修复

### 2. `task_chains` 为扁平数组
**位置：** `collaboration.task_chains`  
**问题：** 返回格式为扁平数组，而非嵌套树结构。  
**示例：**
```json
"task_chains": [
  {"id": "main-chain", "agents": ["main"], "tasks": 5, "status": "completed"}
]
```
**说明：** 目前仅包含从 `/tmp/dragonclaw_processed_ids.json` 构建的一条链式记录。

### 3. 时间戳为 Unix 秒（非毫秒）
**位置：** 全局  
**说明：** `system.uptime_seconds` 使用 Unix 秒级时间戳。部分时间字段（如 `last_update`）使用 ISO 格式字符串。  
**注意：** 与 JavaScript `Date.now()`（毫秒）不同，转换时需注意单位。

### 4. `messages` 字段仅在会话列表中出现
**位置：** `sessions[].messages`  
**问题：** 每个会话对象的 `messages` 字段固定为 `0`，未实现真实消息数统计。

### 5. `limits.requests` 数据不可用
**位置：** `usage.limits.requests`  
**问题：** `used` 和 `limit` 均为 `0` / `null`，类型显示为 `unknown`。  
**说明：** 配额限制信息暂无法从 OpenClaw 获取真实数据。

### 6. 缓存策略
- 高频数据（`agents`、`tasks`、`usage` 等）使用 10 秒 TTL 缓存
- 配置数据（`openclaw_config`）使用 60 秒 TTL 缓存
- 实时性要求高的场景建议使用 `/api/events` SSE 流

### 7. Token 长度验证
**位置：** Token 认证  
**规则：** Token 必须为 32 字符的十六进制字符串，否则返回 400 错误。

---

## 数据文件依赖

| 文件路径 | 用途 |
|----------|------|
| `/tmp/dragonclaw_shared_tasks.json` | 共享任务列表 |
| `/tmp/dragonclaw_agent_coordination.json` | Agent 协作事件 |
| `/tmp/dragonclaw_processed_ids.json` | 已处理任务 ID |
| `/data/.openclaw/agents/*/sessions/*.jsonl` | 会话历史（用量统计来源） |
| `/root/.openclaw/openclaw.json` | OpenClaw 主配置 |
| `/root/.openclaw/workspace/memory/*.md` | 记忆文件 |
| `~/.openclaw/dashboard/.auth_token` | API 认证 Token |
