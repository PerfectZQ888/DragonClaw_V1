# 📋 DragonClaw - 任务模板

## 任务格式

```json
{
  "id": "task_001",
  "title": "任务标题",
  "description": "任务详细描述",
  "assigned_to": "research|creative|dev|perfect",
  "status": "pending|in_progress|completed|blocked",
  "priority": "high|medium|low",
  "blocked_by": [],
  "created_at": "2026-03-22T10:00:00Z",
  "created_by": "main",
  "result": null,
  "tags": ["research", "analysis"]
}
```

## 常用任务模板

### 研究类任务

```json
{
  "id": "",
  "title": "搜索 [主题] 最新资讯",
  "description": "使用 tavily-search 搜索 [主题] 相关的最新资讯，整理成摘要报告",
  "assigned_to": "research",
  "status": "pending",
  "priority": "medium",
  "tags": ["research", "search"]
}
```

### 创作类任务

```json
{
  "id": "",
  "title": "生成 [类型] 内容",
  "description": "根据用户需求，生成 [文章/图片/视频] 内容",
  "assigned_to": "creative",
  "status": "pending",
  "priority": "medium",
  "tags": ["creative", "content"]
}
```

### 开发类任务

```json
{
  "id": "",
  "title": "开发 [功能] 模块",
  "description": "实现 [功能] 的代码开发，包括 [具体需求]",
  "assigned_to": "dev",
  "status": "pending",
  "priority": "high",
  "tags": ["development", "code"]
}
```

### 协作类任务

```json
{
  "id": "",
  "title": "协作任务示例",
  "description": "需要多个 Agent 协作完成",
  "assigned_to": "research",
  "status": "pending",
  "priority": "medium",
  "blocked_by": [],
  "subtasks": [
    {
      "title": "步骤1: 研究分析",
      "assigned_to": "research"
    },
    {
      "title": "步骤2: 生成报告",
      "assigned_to": "creative",
      "blocked_by": ["步骤1"]
    }
  ],
  "tags": ["collaboration"]
}
```

## 任务执行流程

```
创建任务 → 分配 Agent → 执行 → 结果汇报 → main 整合 → 完成
```

## 快速创建命令

```bash
# 在任务目录创建新任务
cd ~/.openclaw/tasks
cat > task_$(date +%Y%m%d_%H%M%S).json << 'EOF'
{
  "id": "task_001",
  "title": "示例任务",
  "description": "任务描述",
  "assigned_to": "research",
  "status": "pending",
  "priority": "medium",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
```
