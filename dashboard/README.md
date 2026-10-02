# DragonClaw Dashboard

DragonClaw 团队实时监控系统。

## 目录结构

```
dashboard/
├── index.html          # 主页入口（系统概览）
├── live.html           # 实时监控页面
├── dashboard.html      # 综合监控页面（多标签）
├── login.html          # 登录页面
├── js/
│   ├── common.js       # 共享工具函数
│   ├── dashboard.js    # 综合监控逻辑
│   ├── index.js        # 主页逻辑
│   └── live.js         # 实时监控逻辑
├── server/             # 后端服务器模块
│   ├── auth.py         # 认证
│   ├── http_handler.py # HTTP 处理
│   └── sse_manager.py  # SSE 管理
├── collectors/         # 数据采集模块
├── api/                # API 模型
├── models/             # 数据模型
├── cache/              # 缓存模块
├── data/               # 运行时数据
├── docs/               # 项目文档
├── logs/               # 日志文件
├── archive/            # 归档文档
└── dashboard_server.py # 主服务器
```

## 页面说明

| 页面 | 用途 | 数据刷新 |
|------|------|----------|
| index.html | 系统概览、Agent状态、任务、Skills | XHR + SSE |
| live.html | 实时监控面板 | SSE 实时推送 |
| dashboard.html | 综合监控（5个标签页） | XHR + SSE |
| login.html | 登录认证 | - |

## 共享库依赖

- `common.js`: escapeHtml, formatNumber, AgentConfig, SSEConnection 等
- `dashboard.js`: 依赖 common.js
- `index.js`: 依赖 common.js
- `live.js`: 依赖 common.js
