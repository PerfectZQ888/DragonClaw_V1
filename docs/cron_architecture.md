# DragonClaw Agent Cron 架构

**更新时间：** 2026-04-10

## 现状分析

### 问题根因
- `sessionTarget: "isolated"` = cron 跑在隔离模式
- **isolated 模式没有 workspace 上下文**，无法读取 session 文件
- 因此需要读文件的任务（记忆更新）都会 timeout

### 验证结果
| Agent | Cron | 问题 |
|-------|------|------|
| research | memory-update-research | ✅ OK（任务简单，18秒完成）|
| dev | memory-update-dev | ✅ OK |
| creative | memory-update-creative | ❌ Timeout（300s）|
| perfect_openclaw | memory-update-perfect | ❌ Timeout（300s）|
| security | 无 | ❌ 无心跳 |

## 当前 Cron 列表

### 心跳 Cron（新建）
| Agent | 名称 | 频率 | 状态 |
|-------|------|------|------|
| research | heartbeat-research | 每30分钟 | ✅ 正常 |
| dev | heartbeat-dev | 每30分钟 | ✅ 正常 |
| security | heartbeat-security | 每30分钟 | ✅ Session 活跃 |

### 记忆更新 Cron（简化）
| Agent | 名称 | 频率 | 状态 |
|-------|------|------|------|
| research | memory-update-research | 每天2次 | ✅ OK |
| dev | memory-update-dev | 每天2次 | ✅ OK |
| creative | memory-update-creative | 每天2次 | ⚠️ 已简化为轻量心跳（60s超时）|
| perfect_openclaw | memory-update-perfect | 每天2次 | ⚠️ 已简化为轻量心跳（60s超时）|

### 系统 Cron
| 名称 | 频率 | 状态 |
|------|------|------|
| skill-security-scan | 每天2次（6:00/18:00）| ✅ OK |
| Memory Dreaming Promotion | 每天3:00 | ✅ OK |

## 架构设计

### 心跳机制（已实现）
- 每个 Agent 每 30 分钟一次轻量心跳
- 任务：回复"心跳正常"（不需要读文件）
- 超时：30秒
- 作用：确认 Agent session 活跃

### 记忆更新（待优化）
- 当前问题：isolated session 无法读文件
- 解决方案：由 **main** 定期聚合各 Agent 记忆
- main 有完整 workspace 上下文，可以读取所有 agent session 文件

### 待完成
1. main 定期聚合各 Agent 记忆（通过 main heartbeat 或独立 cron）
2. creative/perfect_openclaw 的记忆更新任务重新设计
3. security 心跳优化（模型回答内容待调试）

## 心跳 Cron 命令
```bash
# 查看所有 cron
openclaw cron list

# 查看运行历史
openclaw cron runs --id <cron-id>

# 手动触发测试
openclaw cron run <cron-id>

# 删除 cron
openclaw cron rm <cron-id>
```
