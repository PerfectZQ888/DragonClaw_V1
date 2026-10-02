# 🤝 Contributing to DragonClaw

感谢您对 DragonClaw 的兴趣! 我们欢迎任何形式的贡献。

## 📋 贡献方式

### 🐛 报告 Bug
- 在 [Issues](https://github.com/PerfectZQ888/DragonClaw/issues) 提交
- 包含: 复现步骤、期望行为、实际行为、环境信息
- 用 `bug` 标签

### 💡 提出新功能
- 在 Issues 用 `enhancement` 标签
- 描述: 用例、API 设计、替代方案

### 🔧 提交代码
1. 创建特性分支 (`git checkout -b feature/your-feature`)
2. 提交修改 (`git commit -m 'feat: your feature'`)
3. 推送到分支 (`git push origin feature/your-feature`)
4. 创建 Pull Request

## 📝 Commit 规范

我们用 [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` 新功能
- `fix:` 修 bug
- `docs:` 文档
- `style:` 代码格式 (无逻辑变化)
- `refactor:` 重构
- `test:` 加测试
- `chore:` 构建/工具/依赖

## ✅ PR 检查清单

- [ ] 代码风格一致 (PEP 8)
- [ ] 加了必要的测试
- [ ] 更新了相关文档
- [ ] 通过本地测试 (`python -m pytest dashboard/tests/`)
- [ ] 没有引入新警告

## 🧪 本地开发

```bash
git clone https://github.com/PerfectZQ888/DragonClaw.git
cd DragonClaw
pip install -r requirements.txt

# 跑 dashboard
cd dashboard
python dashboard_server.py
# 访问 http://localhost:8888
```

## 📜 许可证

贡献的代码采用 [MIT License](LICENSE)。