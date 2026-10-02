<div align="center">

<img src="assets/dragonclaw-banner.png" alt="DragonClaw Banner" width="100%"/>

# 🦞 DragonClaw

### AI Agent 智能协作团队

[![Version](https://img.shields.io/badge/version-V1.3-blue)](https://github.com/PerfectZQ888/DragonClaw)
[![Platform](https://img.shields.io/badge/platform-Linux%20ARM64-orange)](https://github.com/PerfectZQ888/DragonClaw)
[![Python](https://img.shields.io/badge/python-3.9%2B-green)](https://github.com/PerfectZQ888/DragonClaw)
[![License](https://img.shields.io/badge/license-MIT-yellow)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)
[![Code of Conduct](https://img.shields.io/badge/code%20of%20conduct-Contributor%20Covenant-purple.svg)](./CODE_OF_CONDUCT.md)

---

> 🦞 **"当一群 AI Agent 聚在一起，会发生什么？"**
>
> DragonClaw 给你答案 —— 一个由多智能体驱动的协作平台，  
> 让 AI 不再单打独斗，而是像龙虾群一样**协同作战**。

---

```
    🦞🦞🦞🦞🦞
   ╔═══════════════╗
   ║  DragonClaw   ║
   ║  AI Agent 🦞  ║
   ╚═══════════════╝
    ╱│╲   ╱│╲   ╱│╲
   🤖 🤖 🤖 🤖 🤖 🤖
```

</div>

---

## 🎯 核心能力

| 模块 | 功能 | 状态 |
|------|------|:----:|
| 📊 **Dashboard 监控** | CPU / 内存 / 双磁盘 / 负载实时监控 | ✅ |
| 🤖 **多 Agent 协作** | 任务分发、进度追踪、协作链路可视化 | ✅ |
| 📡 **实时数据** | SSE 推送 + 5 秒自动刷新 | ✅ |
| 🔐 **安全认证** | Token 认证 + 防火墙 + 路径防护 | ✅ |
| 📈 **用量统计** | Token 消耗、请求量、模型调用分析 | ✅ |
| 🛠️ **技能管理** | 43+ 技能自动发现与状态监控 | ✅ |

## 🏗️ 架构一览

```
┌─────────────────────────────────────────────┐
│              🌐 宿主机浏览器                   │
│         http://YOUR_HOST_IP:8888           │
└──────────────────────┬──────────────────────┘
                       │ HTTP + Token Auth
                       ▼
┌─────────────────────────────────────────────┐
│          🔥 firewalld (8888/tcp)             │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│     🦞 dashboard_server.py (Python)          │
│  ┌───────┬──────────┬──────────┬──────────┐  │
│  │  API  │   SSE    │  Static  │  Auth    │  │
│  │ /api/ │ /events  │  *.html  │  Token   │  │
│  └───┬───┴────┬─────┴────┬─────┴────┬─────┘  │
│      │        │          │          │         │
│      ▼        ▼          ▼          ▼         │
│  ┌─────────────────────────────────────────┐  │
│  │  📁 数据源：jsonl / psutil / openclaw   │  │
│  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## 📂 项目结构

```
DragonClaw/
├── 🖥️  dashboard/           # 监控中心
│   ├── index.html           #   Agent 团队总览
│   ├── dashboard.html       #   综合监控 (7 标签页)
│   ├── live.html            #   实时监控看板
│   └── dashboard_server.py  #   后端 API 服务
├── 📋  tasks/               # 任务协调
│   └── coordination/        #   协作任务链路
├── 📚  docs/                # 文档
│   └── GITHUB_SOP.md        #   GitHub 推送指南
├── 🔧  scripts/             # 工具脚本
│   ├── backup_*.sh          #   备份脚本
│   ├── deploy_security.sh   #   安全部署
│   └── dragonclaw-*.service #   systemd 服务
├── 🧠  team-memory/         # 团队记忆
└── 📖  README.md            # 👈 你在这里
```

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone git@github.com:PerfectZQ888/DragonClaw.git
cd DragonClaw

# 2. 安装依赖
pip install psutil

# 3. 启动服务
python3 dashboard/dashboard_server.py

# 4. 获取 Token
TOKEN=$(cat dashboard/.auth_token)

# 5. 访问 Dashboard
# http://localhost:8888?token=${TOKEN}
```

## 📊 Dashboard 预览

| 页面 | 功能 | 截图 |
|:----:|------|------|
| 📊 | **总览** — Agent 状态 / 任务进度 / 系统健康 | 7 标签页 |
| 📈 | **用量** — Token 消耗 / 请求量 / 模型调用 | 实时统计 |
| 👥 | **员工** — Agent 列表 / 状态 / 协作关系 | 可视化 |
| 🔗 | **协作** — 任务链路 / 派发追踪 / 完成度 | 流程图 |
| 📋 | **任务** — 待办 / 进行中 / 已完成 | 看板 |
| 📁 | **文档** — 团队文档 / 知识库 | 文件树 |
| 🧠 | **记忆** — Agent 记忆文件 / 长期记忆 | 自动同步 |

## 🔒 安全特性

- ✅ **Token 认证** — 所有 API 端点需要 Token
- ✅ **防火墙集成** — firewalld 端口管控
- ✅ **敏感文件保护** — .gitignore 排除 .auth_token / openclaw.json
- ✅ **路径遍历防护** — 文件服务 abspath 校验
- ✅ **401 自动跳转** — 无 Token 引导至首页

## 📈 版本历史

| 版本 | 日期 | 亮点 |
|:----:|------|------|
| **V1.3** | 2026-03-29 | 安全加固 · Token 认证 · 多磁盘监控 |
| V1.2 | 2026-03-28 | 技能管理 · Dashboard 初版 · 微信通道 |
| V1.1 | 2026-03-24 | Agent 模型配置 · 协作方案 |
| V1.0 | 2026-03-23 | 项目初始化 |

---

## 📜 License

本项目采用 **MIT License** 开源, 您可以:
- ✅ 自由使用、复制、修改、合并、发布、分发、再授权
- ✅ 商用
- ⚠️ 唯一要求: 保留版权声明

详见 [LICENSE](./LICENSE) 文件。

## 🤝 Contributing

欢迎贡献! 详情见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

社区规范见 [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)。

## 🔒 安全

发现安全漏洞? 请通过 [GitHub Security Advisories](https://github.com/PerfectZQ888/DragonClaw/security/advisories/new) 私下报告, 不要在公开 Issue 中披露。

详见 [SECURITY.md](./SECURITY.md)。

---

<div align="center">

### 🦞 DragonClaw — 让 AI 团队协作不再是梦

*Built with ❤️ by PerfectZQ888 & 帝钳统帅*

![DragonClaw](https://img.shields.io/badge/DragonClaw-🦞-red?style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==)

</div>
