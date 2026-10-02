# DragonClaw 版本信息

---

## V2.0 - 2026-03-27

### 系统升级
- OpenClaw 框架升级至 2026.3.24
- Node.js 运行时升级至 22.22.1
- 监控平台：Vanilla JS 前端 + Python SSE 实时推送

### 渠道对接
- 飞书渠道：已配置，支持私聊和群聊
- QQ Bot 渠道：已配置并启用
- 微信渠道：已对接，登录成功

### 文档更新
- 新增 `DragonClaw-install-2026-03-27.md` 安装部署手册
- 完善插件安装指南（官方/第三方/渠道扩展）
- 新增账号配置说明（`openclaw configure` 交互式配置）
- 添加插件信任配置 (`plugins.allow`)
- 新增备份脚本 `scripts/backup_openclaw.sh`
- 新增 `backup_manual.md` 备份恢复操作手册

### Agent 团队
| Agent | 状态 | 模型 | 协调能力 |
|-------|------|------|----------|
| main | ✅ 运行中 | glm-4.7-flash | → research/creative/dev/perfect |
| research | ✅ 运行中 | glm-4.7-flash | → main/creative/dev |
| creative | ✅ 运行中 | glm-4.7-flash | → main/research/dev |
| dev | ✅ 运行中 | glm-4.7-flash | → main/research/creative |
| perfect_openclaw | ✅ 运行中 | glm-4.7-flash | → main/research/creative/dev |
| security | ✅ 运行中 | glm-4.7-flash | - |
| skill-vetter | ✅ 运行中 | glm-4.7-flash | - |
| perfect_openclaw | ✅ 运行中 | glm-4.7-flash |
| security | ✅ 运行中 | glm-4.7-flash |
| skill-vetter | ✅ 运行中 | glm-4.7-flash |

### 技能统计
- 已安装技能：38/74 ready
- 主要技能：tavily-search, weather, feishu-doc, feishu-drive, notion 等

### Gateway 配置
- 端口：18789
- 状态：running
- 协议：WebSocket

### Agent 协调配置
- 已配置双向 subagents.allowAgents
- 核心 Agent 可相互 spawn 子任务
- 测试报告：`/data/DragonClaw/tasks/coordination/agent_coordination_test.md`
- 新增 Agent 协调监控：`dashboard/agent_coordinator.py`
- 新增 API 端点：`/api/coordination`
- Dashboard 可显示 Agent 协作任务

---

## V1.0 - 2026-03-24

### 初始版本

#### 功能更新
1. 实时任务监控 - 3秒自动检测飞书任务
2. 综合监控面板 - 总览/用量/员工/协作/任务/文档/记忆
3. Token 消耗统计 - 今日零点到当前时间计算
4. Agent 记忆状态 - 显示各 Agent 记忆配置
5. 文档路径展示 - 显示完整文件路径
6. 时间戳修复 - 转换为北京时间显示
7. Cron 任务过滤 - 排除系统 cron 任务显示
8. 模型配置展示 - 显示所有可用模型

#### 备份文件
- backup_20260324_143000.tar.gz - DragonClaw 主目录备份
- openclaw_config_20260324_143000.tar.gz - OpenClaw 配置备份

---

## 备份文件

| 日期 | 位置 | 内容 |
|------|------|------|
| 2026-03-26 | backup/2026-03-26/ | 完整备份 |
| 2026-03-24 | backup/2026-03-24/ | 完整备份 + OpenClaw 配置 |
| 2026-03-23 | backup/2026-03-23/ | 完整备份 |
| 2026-03-22 | backup/2026-03-22/ | 早期备份（dashboard源码、迁移脚本） |

---

*最后更新: 2026-03-27*
