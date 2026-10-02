# 🦞 DragonClaw - 成员卡片

## 主调度 (main)

```yaml
名称: 主调度
ID: main
角色: 调度中枢
飞书: 私聊
模型: zai/glm-4.7-flash
技能:
  - find-skills
  - skill-manager
  - skill-vetter
  - self-improvement
  - agent-memory
  - weather
  - summarize
特点:
  - 任务分发
  - 意图识别
  - 结果整合
```

## 研究助手 (research)

```yaml
名称: 研究助手
ID: research
角色: 知识探索
飞书: OpenClaw-研究助手群
模型: zai/glm-4.7-flash
技能:
  - openclaw-tavily-search
  - blogwatcher
  - agent-memory
  - file-access
  - nano-pdf
  - summarize
特点:
  - 联网搜索
  - 资讯整理
  - PDF 分析
  - 数据分析
```

## 创意助手 (creative)

```yaml
名称: 创意助手
ID: creative
角色: 内容创作
飞书: OpenClaw-创意助手群
模型: zai/glm-4.7-flash
技能:
  - openai-image-gen
  - cogvideo-generator
  - office-docs
  - office-generator-py
  - word-docx
  - docx-helper
  - feishu-doc-manager
  - wanxiang-video
  - agent-memory
特点:
  - 写作创作
  - 图片生成
  - 视频制作
  - 文档生成
```

## 开发助手 (dev)

```yaml
名称: 开发助手
ID: dev
角色: 软件开发
飞书: OpenClaw-开发助手群
模型: zai/glm-4.7-flash
技能:
  - github-cli
  - skill-manager
  - skill-vetter
  - self-improvement
  - filesystem-access
  - agent-memory
特点:
  - 代码开发
  - Git 操作
  - 调试排错
  - 代码审查
```

## 完美助手 (perfect_openclaw)

```yaml
名称: 完美助手
ID: perfect_openclaw
角色: 深度分析
飞书: 无（直接调用）
模型: zai/glm-4.7-flash
技能:
  - agent-memory
  - file-access
  - filesystem-access
  - notion
  - obsidian
  - clawdhub
  - summarize
特点:
  - 长对话
  - 复杂推理
  - 深度分析
  - 记忆系统
```

## 安全审查 (skill-vetter)

```yaml
名称: 安全审查
ID: skill-vetter
角色: 质量把控
触发方式: 被动（安装新 Skill 时自动触发）
模型: zai/glm-4.7-flash
技能:
  - skill-vetter
特点:
  - 技能安装前安全扫描
  - 代码审查
  - 依赖检查
  - 恶意代码检测
```

## 安全守护 (security)

```yaml
名称: 安全守护
ID: security
角色: 安全监控
触发方式: 主动（定时/手动）
模型: zai/glm-4.7-flash
技能:
  - skill-vetter
  - skill-manager
  - agent-memory
  - filesystem-access
特点:
  - 定时安全扫描
  - 安全日志审计
  - 风险评估
  - 安全报告生成
```

---

## 安全双保险

| 属性 | skill-vetter | security |
|------|--------------|----------|
| **触发方式** | 被动（安装时） | 主动（定时/手动） |
| **职责** | 安装前扫描 | 持续监控 |
| **使用场景** | clawhub install | 日常审计 |
| **协作关系** | 被 security 调用 | 调用 skill-vetter |
