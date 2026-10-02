# 🚀 DragonClaw - 快速开始

## 立即使用

### 飞书

| 群聊 | 输入示例 |
|------|----------|
| 私聊 (main) | `你好，帮我分析下最近 AI 领域的进展` |
| 研究群 | `搜索量子计算的最新进展` |
| 创意群 | `帮我写一篇关于春天的散文` |
| 开发群 | `帮我写一个 Python 快速排序函数` |

### 命令行

```bash
# 进入 OpenClaw
openclaw

# 切换 Agent
/agent research   # 研究助手
/agent creative   # 创意助手
/agent dev        # 开发助手

# 其他命令
/new              # 新会话
/agents list      # 查看所有 Agent
/help             # 帮助
```

## 团队协作示例

### 场景1: 综合研究报告

```
用户 (私聊): 帮我研究一下 2026 年 AI Agent 的发展趋势

main 接收 → 分发给 research
research 执行搜索和分析
research 汇报结果给 main
main 整合结果 → 用户
```

### 场景2: 完整项目开发

```
用户 (私聊): 帮我做一个待办事项 Web 应用

main 接收 → 分发给 dev
dev 完成需求分析和代码开发
dev 汇报结果给 main
main 整合结果 → 用户
```

### 场景3: 多 Agent 协作

```
用户 (私聊): 研究这个技术方案并生成演示文稿

main 分发:
  - research: 研究技术方案
  - creative: 生成演示文稿

research + creative 完成后汇报
main 整合 → 用户
```

## 查看团队状态

```bash
# 查看 Agent 列表
openclaw agents list

# 查看飞书连接状态
openclaw channels status

# 查看团队日志
cat ~/.openclaw/team/cron.log

# 查看任务队列
ls ~/.openclaw/tasks/
```

## 团队资源

| 资源 | 位置 |
|------|------|
| 团队文档 | `/data/DragonClaw/` |
| 配置文件 | `~/.openclaw/openclaw.json` |
| 团队目录 | `~/.openclaw/team/` |
| 任务队列 | `~/.openclaw/tasks/` |

---

*有问题？发送 `/help` 或联系团队管理员*
